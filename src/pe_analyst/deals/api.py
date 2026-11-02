"""Runs the full agentic underwriting workflow and returns one consolidated report.

Stages run in order -- financial, valuation, scenario, risk, due diligence, industry, investment
committee, IC debate, memo -- and fail fast; a failed stage is reported on the response rather
than raised, so a non-2xx status here means a malformed request, not an unfavorable deal.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

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
from pe_analyst.document_intelligence.agent_inputs import (
    build_due_diligence_inputs,
    build_industry_inputs,
)
from pe_analyst.document_intelligence.financial_mapping import map_financial_statements
from pe_analyst.document_intelligence.schemas import DocumentIntelligenceReport
from pe_analyst.document_intelligence.storage import DocumentReportStore
from pe_analyst.engines.financial.models import FinancialStatement
from pe_analyst.market_data import MarketDataProviderError, build_market_data_provider

from .schemas import DealAnalysisRequest, SensitivityRequest

router = APIRouter(prefix="/deals", tags=["deal-analysis"])


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


@router.post(
    "/analyze",
    response_model=UnifiedDealReport,
    summary="Run the full agentic underwriting workflow for one company",
)
def analyze_deal(
    request: DealAnalysisRequest,
    settings: Settings = Depends(get_settings),  # noqa: B008
    narrator: Narrator | None = Depends(get_narrator),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> UnifiedDealReport:
    industry_inputs = request.industry_inputs
    due_diligence_inputs = request.due_diligence_inputs
    needs_financials = request.current_financials is None or request.previous_financials is None
    document: DocumentIntelligenceReport | None = None

    if request.document_id and (
        needs_financials or industry_inputs is None or due_diligence_inputs is None
    ):
        document = DocumentReportStore.load(request.document_id, settings)
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

    if (
        request.current_financials is not None
        and request.previous_financials is not None
    ):
        current = FinancialStatement(**request.current_financials.model_dump())
        previous = FinancialStatement(**request.previous_financials.model_dump())
    elif document is not None:
        try:
            current, previous = map_financial_statements(document).statements(
                request.financial_overrides
            )
        except ValueError as error:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error
    else:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Provide current_financials and previous_financials, or a document_id to derive them",
        )

    inputs = DealAnalysisInputs(
        company_name=request.company_name,
        financial_data={"current": current, "previous": previous},
        valuation_inputs=resolve_peers(request.valuation_inputs, settings),
        industry_inputs=industry_inputs or {},
        risk_inputs=request.risk_inputs,
        due_diligence_inputs=due_diligence_inputs,
        scenario_inputs=request.scenario_inputs,
    )
    return run_deal_analysis(inputs, narrator=narrator)


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


__all__ = ["get_narrator", "resolve_peers", "router"]
