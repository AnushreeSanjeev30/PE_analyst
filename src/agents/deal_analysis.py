"""Single entry point for the end-to-end PE underwriting workflow.

``run_deal_analysis`` is the one function a caller (API route, CLI, notebook)
needs: hand it validated deal inputs and it drives Financial -> Valuation ->
Scenario -> Risk -> Due Diligence -> Industry -> Investment Committee -> IC
debate -> Investment Memo through :class:`DealAnalysisOrchestrator`
and hands back a single :class:`UnifiedDealReport` -- complete on success,
partial (with the failed stage identified) if a stage raised.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID

from .due_diligence_models import DueDiligenceReport
from .financial_models import FinancialReport
from .ic_simulation_models import ICDecision
from .industry_models import IndustryReport
from .investment_models import InvestmentCommitteeReport
from .memo_models import InvestmentMemo
from .narration import Narrative, Narrator
from .orchestrator import DealAnalysisOrchestrator
from .orchestrator_models import AgentRunRecord, RunStatus
from .risk_models import RiskReport
from .scenario_models import ScenarioReport
from .state import AgentState
from .valuation_models import ValuationReport


@dataclass(slots=True)
class DealAnalysisInputs:
    """Everything required to underwrite a single company in one run.

    ``financial_data`` must contain ``current`` and ``previous``
    ``FinancialStatement`` objects. ``valuation_inputs`` must contain
    ``dcf``, ``comparables``, and ``lbo`` keys. ``industry_inputs`` must
    contain ``industry_name`` and source-grounded ``evidence`` (see
    :class:`pe_analyst.document_intelligence.DocumentIntelligenceService`,
    whose ``industry_evidence`` output is already shaped for this field).
    ``due_diligence_inputs`` is an optional list of source-grounded items
    (see ``document_intelligence.agent_inputs.build_due_diligence_inputs``,
    which shapes a document's extracted risk factors and notes for this
    field) that the Due Diligence Agent scores for red flags; an empty or
    omitted list means no diligence evidence was supplied, not a clean bill.
    """

    company_name: str
    financial_data: dict[str, Any]
    valuation_inputs: dict[str, Any]
    industry_inputs: dict[str, Any]
    risk_inputs: dict[str, Any] | None = None
    due_diligence_inputs: list[dict[str, Any]] | None = None
    scenario_inputs: dict[str, Any] | None = None


@dataclass(slots=True)
class UnifiedDealReport:
    """Consolidated, audit-ready output of one deal-analysis run."""

    run_id: UUID
    company_name: str
    status: RunStatus
    started_at: datetime | None
    completed_at: datetime | None
    stages: list[AgentRunRecord]
    financial_report: FinancialReport | None = None
    valuation_report: ValuationReport | None = None
    scenario_report: ScenarioReport | None = None
    risk_report: RiskReport | None = None
    industry_report: IndustryReport | None = None
    due_diligence_report: DueDiligenceReport | None = None
    investment_committee_report: InvestmentCommitteeReport | None = None
    ic_decision: ICDecision | None = None
    investment_memo: InvestmentMemo | None = None
    narratives: dict[str, Narrative] = field(default_factory=dict)
    final_recommendation: str | None = None
    failed_stage: str | None = None
    error: str | None = None

    @property
    def is_complete(self) -> bool:
        return self.status == RunStatus.COMPLETED


def build_agent_state(inputs: DealAnalysisInputs) -> AgentState:
    """Translate validated deal inputs into the shared workflow state."""

    state = AgentState(company_name=inputs.company_name, financial_data=inputs.financial_data)
    state.metadata["valuation_inputs"] = inputs.valuation_inputs
    state.metadata["industry_inputs"] = inputs.industry_inputs
    if inputs.risk_inputs is not None:
        state.metadata["risk_inputs"] = inputs.risk_inputs
    state.metadata["due_diligence_inputs"] = inputs.due_diligence_inputs or []
    if inputs.scenario_inputs is not None:
        state.metadata["scenario_inputs"] = inputs.scenario_inputs
    return state


def run_deal_analysis(
    inputs: DealAnalysisInputs,
    *,
    orchestrator: DealAnalysisOrchestrator | None = None,
    narrator: Narrator | None = None,
) -> UnifiedDealReport:
    """Run the full underwriting workflow and return one consolidated report.

    Stages run in underwriting order and fail fast: if a stage raises, the
    orchestrator marks it FAILED, marks every downstream stage SKIPPED, and
    stops. Whatever specialist reports completed before the failure are still
    returned on the unified report, alongside ``failed_stage`` and ``error``.

    ``narrator`` (see :func:`agents.narration.build_narrator`) adds LLM commentary to each
    stage; it is ignored when an explicit ``orchestrator`` is supplied.
    """

    state = build_agent_state(inputs)
    result = (orchestrator or DealAnalysisOrchestrator(narrator=narrator)).run(state)
    failed_stage = next(
        (record.stage for record in result.stages if record.status == RunStatus.FAILED), None
    )
    return UnifiedDealReport(
        run_id=result.run_id,
        company_name=state.company_name,
        status=result.status,
        started_at=result.started_at,
        completed_at=result.completed_at,
        stages=result.stages,
        financial_report=state.metadata.get("financial_report"),
        valuation_report=state.metadata.get("valuation_report"),
        scenario_report=state.metadata.get("scenario_report"),
        risk_report=state.metadata.get("risk_report"),
        industry_report=state.metadata.get("industry_report"),
        due_diligence_report=state.metadata.get("due_diligence_report"),
        investment_committee_report=state.metadata.get("investment_committee_report"),
        ic_decision=state.metadata.get("ic_decision"),
        investment_memo=state.metadata.get("investment_memo"),
        narratives=state.metadata.get("narratives", {}),
        final_recommendation=result.final_recommendation,
        failed_stage=failed_stage,
        error=result.error,
    )
