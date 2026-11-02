"""Deal Partner: builds the case for doing the deal from the specialist reports."""

from __future__ import annotations

from .base_agent import BaseAgent
from .ic_simulation_tools import DealPartnerTools
from .state import AgentState
from .types import AgentResponse


class DealPartnerAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Deal Partner")
        self.tools = DealPartnerTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        self.tools.required_reports(state)

    def execute(self, state: AgentState) -> AgentResponse:
        financial, valuation, industry = self.tools.required_reports(state)
        opinion = self.tools.evaluate(financial, valuation, industry)
        state.metadata["deal_partner_opinion"] = opinion
        return AgentResponse(
            self.name,
            opinion.rationale,
            0.85,
            opinion.thesis,
            {"opinion": opinion},
        )
