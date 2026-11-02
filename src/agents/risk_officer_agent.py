"""Risk Officer: the committee's skeptic, with veto power over a critical finding."""

from __future__ import annotations

from .base_agent import BaseAgent
from .ic_simulation_tools import RiskOfficerTools
from .state import AgentState
from .types import AgentResponse


class RiskOfficerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Risk Officer")
        self.tools = RiskOfficerTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        self.tools.required_reports(state)

    def execute(self, state: AgentState) -> AgentResponse:
        risk, due_diligence, valuation = self.tools.required_reports(state)
        opinion = self.tools.evaluate(risk, due_diligence, valuation)
        state.metadata["risk_officer_opinion"] = opinion
        return AgentResponse(
            self.name,
            opinion.rationale,
            0.85,
            opinion.objections,
            {"opinion": opinion},
        )
