"""Operating Partner: judges whether there's a credible operational value-creation path."""

from __future__ import annotations

from .base_agent import BaseAgent
from .ic_simulation_tools import OperatingPartnerTools
from .state import AgentState
from .types import AgentResponse


class OperatingPartnerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Operating Partner")
        self.tools = OperatingPartnerTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        self.tools.required_reports(state)

    def execute(self, state: AgentState) -> AgentResponse:
        valuation, industry = self.tools.required_reports(state)
        opinion = self.tools.evaluate(valuation, industry)
        state.metadata["operating_partner_opinion"] = opinion
        return AgentResponse(
            self.name,
            opinion.rationale,
            0.85,
            opinion.value_levers,
            {"opinion": opinion},
        )
