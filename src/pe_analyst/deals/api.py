"""Runs the full agentic underwriting workflow and keeps every run.

Stages run in order -- financial, valuation, scenario, risk, due diligence, industry, investment
committee, IC debate, memo -- and fail fast; a failed stage is reported on the report rather
than raised, so a non-2xx status here means a malformed request, not an unfavorable deal.

Two ways to run an analysis, both saved to ``deal_analyses`` under the caller:

* ``POST /deals/analyses`` returns immediately with an id and runs in the background. Poll
  ``GET /deals/analyses/{id}`` until ``status`` is ``completed`` or ``failed``. This is what the
  frontend uses: a narrated run makes a dozen LLM calls and can outlast a proxy's request
  timeout.
* ``POST /deals/analyze`` blocks and returns the finished report -- convenient for scripts.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any
from uuid import UUID, uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response, status
from pydantic import TypeAdapter
from sqlalchemy.orm import Session

from agents import (
    DealAnalysisInputs,
    Narrator,
    UnifiedDealReport,
    build_narrator,
    run_deal_analysis,
)
from lbo.assumptions import LBOAssumptions
from lbo.schemas import OperatingProjection
from lbo.sensitivity import SensitivityEngine, SensitivityGrid
from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.core.logging import get_logger
from pe_analyst.db.session import SessionFactory, get_db_session, get_session_factory
from pe_analyst.document_intelligence.agent_inputs import (
    build_due_diligence_inputs,
    build_financial_evidence,
    build_industry_inputs,
)
from pe_analyst.document_intelligence.financial_mapping import map_financial_statements
from pe_analyst.document_intelligence.repository import load_visible_report
from pe_analyst.document_intelligence.schemas import DocumentIntelligenceReport
from pe_analyst.engines.financial.models import FinancialStatement
from pe_analyst.market_data import MarketDataProviderError, build_market_data_provider

from .repository import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    DealAnalysisRepository,
)
from .schemas import (
    DealAnalysisRecord,
    DealAnalysisRequest,
    DealAnalysisSummary,
    SensitivityRequest,
)

router = APIRouter(prefix="/deals", tags=["deal-analysis"])
logger = get_logger(__name__)

_REPORT_ADAPTER: TypeAdapter[UnifiedDealReport] = TypeAdapter(UnifiedDealReport)


def get_narrator(settings: Settings = Depends(get_settings)) -> Narrator | None:  # noqa: B008
    """The configured LLM narrator, or None (fully deterministic) without credentials."""

    return build_narrator(settings)


def resolve_peers(valuation_inputs: dict[str, Any], settings: Settings) -> dict[str, Any]:
    """Fill ``comparables.peers`` from ``comparables.peer_tickers`` via the market-data vendor.

    Explicit ``peers`` always win; tickers are only looked up when no peers were supplied.
    """

    comparables = valuation_inputs.get("comparables")
    if not isinstance(comparables, dict) or comparables.get("peers"):
        return valuation_inputs
    tickers = comparables.get("peer_tickers")
    if not tickers:
        return valuation_inputs
    query = tickers if isinstance(tickers, str) else ",".join(str(item) for item in tickers)
    try:
        peers = build_market_data_provider(settings).get_comparable_companies(query)
    except MarketDataProviderError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    return {
        **valuation_inputs,
        "comparables": {**comparables, "peers": [asdict(peer) for peer in peers]},
    }


def build_inputs(
    request: DealAnalysisRequest,
    settings: Settings,
    session: Session,
    current_user: UserPublic,
) -> DealAnalysisInputs:
    """Validate a request into workflow inputs, raising the right 4xx for anything unusable.

    Everything that can be rejected is rejected here, before a run is created, so a background
    run never fails for a reason the caller could have been told about up front.
    """

    industry_inputs = request.industry_inputs
    due_diligence_inputs = request.due_diligence_inputs
    needs_financials = request.current_financials is None or request.previous_financials is None
    document: DocumentIntelligenceReport | None = None
    financial_evidence: list[dict[str, Any]] = []

    if request.document_id and (
        needs_financials or industry_inputs is None or due_diligence_inputs is None
    ):
        document = load_visible_report(request.document_id, current_user, session, settings)
        if document is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, f"No document found with id {request.document_id}"
            )
        if industry_inputs is None:
            if not request.industry_name:
                raise HTTPException(
                    status.HTTP_400_BAD_REQUEST,
                    "industry_name is required to derive industry_inputs from document_id",
                )
            industry_inputs = build_industry_inputs(document, industry_name=request.industry_name)
        if due_diligence_inputs is None:
            due_diligence_inputs = build_due_diligence_inputs(document)

    if request.current_financials is not None and request.previous_financials is not None:
        current = FinancialStatement(**request.current_financials.model_dump())
        previous = FinancialStatement(**request.previous_financials.model_dump())
    elif document is not None:
        mapped = map_financial_statements(document)
        try:
            current, previous = mapped.statements(request.financial_overrides)
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
        financial_evidence = build_financial_evidence(document, mapped)
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide current_financials and previous_financials, or a document_id to derive them",
        )

    return DealAnalysisInputs(
        company_name=request.company_name,
        financial_data={"current": current, "previous": previous},
        valuation_inputs=resolve_peers(request.valuation_inputs, settings),
        industry_inputs=industry_inputs or {},
        risk_inputs=request.risk_inputs,
        due_diligence_inputs=due_diligence_inputs,
        scenario_inputs=request.scenario_inputs,
        financial_evidence=financial_evidence,
    )


def _save_outcome(
    repository: DealAnalysisRepository, analysis_id: str, report: UnifiedDealReport
) -> None:
    repository.finish(
        analysis_id,
        status=STATUS_COMPLETED if report.is_complete else STATUS_FAILED,
        report=_REPORT_ADAPTER.dump_python(report, mode="json"),
        recommendation=report.final_recommendation,
        error=report.error,
    )


def run_and_store(
    analysis_id: str,
    inputs: DealAnalysisInputs,
    narrator: Narrator | None,
    session_factory: SessionFactory,
) -> None:
    """Background job: run the workflow and record the outcome. Never raises."""

    with session_factory() as session:
        repository = DealAnalysisRepository(session)
        try:
            repository.mark_running(analysis_id)
            report = run_deal_analysis(inputs, narrator=narrator)
            report.run_id = UUID(analysis_id)
            _save_outcome(repository, analysis_id, report)
        except Exception as error:  # noqa: BLE001 - the caller is gone; record, don't raise
            logger.exception("Deal analysis %s crashed", analysis_id)
            session.rollback()
            repository.finish(
                analysis_id,
                status=STATUS_FAILED,
                report=None,
                recommendation=None,
                error=f"{type(error).__name__}: {error}",
            )


@router.post(
    "/analyses",
    response_model=DealAnalysisSummary,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Start an underwriting run in the background and return its id",
)
def start_analysis(
    request: DealAnalysisRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings),  # noqa: B008
    narrator: Narrator | None = Depends(get_narrator),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    session_factory: SessionFactory = Depends(get_session_factory),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DealAnalysisSummary:
    inputs = build_inputs(request, settings, session, current_user)
    analysis = DealAnalysisRepository(session).create(
        owner_id=current_user.id,
        company_name=request.company_name,
        document_id=request.document_id,
        request=request.model_dump(mode="json"),
    )
    background_tasks.add_task(run_and_store, analysis.id, inputs, narrator, session_factory)
    return DealAnalysisSummary.model_validate(analysis)


@router.get(
    "/analyses",
    response_model=list[DealAnalysisSummary],
    summary="List the caller's saved analyses, newest first",
)
def list_analyses(
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> list[DealAnalysisSummary]:
    return [
        DealAnalysisSummary.model_validate(analysis)
        for analysis in DealAnalysisRepository(session).list_for(current_user)
    ]


@router.get(
    "/analyses/{analysis_id}",
    response_model=DealAnalysisRecord,
    summary="Fetch one saved analysis: its status and, once finished, the full report",
)
def get_analysis(
    analysis_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DealAnalysisRecord:
    analysis = DealAnalysisRepository(session).get(analysis_id, current_user)
    if analysis is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No analysis found with id {analysis_id}")
    return DealAnalysisRecord.model_validate(analysis)


@router.delete(
    "/analyses/{analysis_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete one saved analysis",
)
def delete_analysis(
    analysis_id: str,
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> Response:
    if not DealAnalysisRepository(session).delete(analysis_id, current_user):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No analysis found with id {analysis_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/analyze",
    response_model=UnifiedDealReport,
    summary="Run the full agentic underwriting workflow, wait for it, and save the report",
)
def analyze_deal(
    request: DealAnalysisRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
    narrator: Narrator | None = Depends(get_narrator),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> UnifiedDealReport:
    inputs = build_inputs(request, settings, session, current_user)
    report = run_deal_analysis(inputs, narrator=narrator)

    # ``run_id`` doubles as the saved analysis id, so the caller can fetch this report again
    # from GET /deals/analyses/{run_id}.
    analysis_id = str(uuid4())
    report.run_id = UUID(analysis_id)
    repository = DealAnalysisRepository(session)
    repository.create(
        owner_id=current_user.id,
        company_name=request.company_name,
        document_id=request.document_id,
        request=request.model_dump(mode="json"),
        analysis_id=analysis_id,
    )
    _save_outcome(repository, analysis_id, report)
    return report


@router.post(
    "/sensitivity",
    response_model=SensitivityGrid,
    summary="Compute a two-way IRR/MOIC sensitivity grid (exit multiple x EBITDA) for one LBO case",
)
def sensitivity_grid(
    request: SensitivityRequest,
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> SensitivityGrid:
    try:
        assumptions = LBOAssumptions(**request.lbo_assumptions)
        assumptions.validate()
        projection = [OperatingProjection(**item) for item in request.operating_projection]
        engine = SensitivityEngine(assumptions, projection)
        return engine.grid(request.exit_multiples, request.ebitda_multipliers)
    except (TypeError, ValueError) as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error


__all__ = ["build_inputs", "get_narrator", "resolve_peers", "router", "run_and_store"]
