"""Fail-fast, observable orchestration for the PE underwriting agent workflow."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .base_agent import BaseAgent
from .deal_partner_agent import DealPartnerAgent
from .due_diligence_agent import DueDiligenceAgent
from .financial_agent import FinancialAgent
from .ic_chairperson_agent import ICChairpersonAgent
from .industry_agent import IndustryAgent
from .investment_agent import InvestmentCommitteeAgent
from .memo_agent import InvestmentMemoAgent
from .operating_partner_agent import OperatingPartnerAgent
from .orchestrator_models import AgentRunRecord, DealAnalysisResult, RunStatus
from .risk_agent import RiskAgent
from .risk_officer_agent import RiskOfficerAgent
from .scenario_agent import ScenarioAnalysisAgent
from .state import AgentState
from .valuation_agent import ValuationAgent

if TYPE_CHECKING:
    from .narration import Narrator


class DealAnalysisOrchestrator:
    """Runs agents in underwriting order and persists a complete execution trace."""

    def __init__(
        self,
        agents: Sequence[tuple[str, BaseAgent]] | None = None,
        *,
        narrator: Narrator | None = None,
    ) -> None:
        self.agents = list(
            agents
            or [
                ("financial", FinancialAgent()),
                ("valuation", ValuationAgent()),
                ("scenario", ScenarioAnalysisAgent()),
                ("risk", RiskAgent()),
                ("due_diligence", DueDiligenceAgent()),
                ("industry", IndustryAgent()),
                ("investment_committee", InvestmentCommitteeAgent()),
                ("deal_partner", DealPartnerAgent()),
                ("risk_officer", RiskOfficerAgent()),
                ("operating_partner", OperatingPartnerAgent()),
                ("chairperson", ICChairpersonAgent()),
                ("memo", InvestmentMemoAgent()),
            ]
        )
        if narrator is not None:
            for _, agent in self.agents:
                agent.narrator = narrator

    def run(self, state: AgentState) -> DealAnalysisResult:
        result = DealAnalysisResult(status=RunStatus.RUNNING, started_at=self._now())
        state.metadata["orchestration"] = result
        for stage, agent in self.agents:
            record = AgentRunRecord(
                stage=stage, agent_name=agent.name, status=RunStatus.RUNNING, started_at=self._now()
            )
            result.stages.append(record)
            try:
                record.response = agent.run(state)
                record.status = RunStatus.COMPLETED
                record.completed_at = self._now()
            except Exception as error:
                record.status = RunStatus.FAILED
                record.completed_at = self._now()
                record.error = f"{type(error).__name__}: {error}"
                result.status = RunStatus.FAILED
                result.error = f"Stage '{stage}' failed: {record.error}"
                result.completed_at = self._now()
                self._append_skipped_records(result, state, stage)
                return result
        result.status = RunStatus.COMPLETED
        result.completed_at = self._now()
        result.final_recommendation = state.recommendation.get("recommendation")
        return result

    def _append_skipped_records(
        self, result: DealAnalysisResult, state: AgentState, failed_stage: str
    ) -> None:
        failed_index = next(
            index for index, (stage, _) in enumerate(self.agents) if stage == failed_stage
        )
        for stage, agent in self.agents[failed_index + 1 :]:
            result.stages.append(
                AgentRunRecord(stage=stage, agent_name=agent.name, status=RunStatus.SKIPPED)
            )

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)
