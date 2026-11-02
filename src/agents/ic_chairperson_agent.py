"""IC Chairperson: rules on the final recommendation from the committee vote and the debate."""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .ic_simulation_models import ICDecision
from .ic_simulation_tools import ChairpersonTools
from .state import AgentState
from .types import AgentResponse


class ICChairpersonAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("IC Chairperson")
        self.tools = ChairpersonTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        self._required(state)

    def execute(self, state: AgentState) -> AgentResponse:
        committee_report, deal_partner, risk_officer, operating_partner = self._required(state)

        final, dissent, rationale = self.tools.rule(
            committee_report.summary.recommendation.value,
            deal_partner,
            risk_officer,
            operating_partner,
        )

        decision = ICDecision(
            company_name=state.company_name,
            final_recommendation=final,
            unanimous=not dissent,
            chair_rationale=rationale,
            committee_vote=committee_report,
            deal_partner=deal_partner,
            risk_officer=risk_officer,
            operating_partner=operating_partner,
            dissent=dissent,
        )
        state.recommendation = {"decision": decision, "recommendation": final}
        state.metadata["ic_decision"] = decision
        return AgentResponse(
            self.name,
            rationale,
            0.90 if decision.unanimous else 0.70,
            [f"{item.member} dissents" for item in dissent],
            {"decision": decision},
        )

    @staticmethod
    def _required(state: AgentState) -> tuple[Any, Any, Any, Any]:
        reports = (
            state.metadata.get("investment_committee_report"),
            state.metadata.get("deal_partner_opinion"),
            state.metadata.get("risk_officer_opinion"),
            state.metadata.get("operating_partner_opinion"),
        )
        if any(report is None for report in reports):
            raise ValueError(
                "IC Chairperson requires the committee vote and all three partner opinions"
            )
        return reports
