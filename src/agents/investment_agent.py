"""Investment Committee Agent for final, policy-driven underwriting opinions."""

from __future__ import annotations

from .base_agent import BaseAgent
from .investment_models import (
    CommitteeRecommendation,
    InvestmentCommitteeReport,
    InvestmentCommitteeSummary,
)
from .investment_tools import InvestmentTools
from .state import AgentState
from .types import AgentResponse


class InvestmentCommitteeAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Investment Committee Agent")
        self.tools = InvestmentTools()

    def validate(self, state: AgentState) -> None:
        super().validate(state)
        self.tools.required_reports(state)

    def execute(self, state: AgentState) -> AgentResponse:
        financial, valuation, risk, industry = self.tools.required_reports(state)
        votes = [
            self.tools.vote_financial(financial),
            self.tools.vote_valuation(valuation),
            self.tools.vote_risk(risk),
            self.tools.vote_industry(industry),
        ]
        support_weight = sum(vote.weight for vote in votes if vote.outcome == "SUPPORT")
        recommendation = self._recommendation(
            support_weight, valuation.lbo_returns.irr, risk.summary.level.value
        )
        confidence = min(0.95, max(0.35, support_weight * 0.85 + 0.10))
        top_risks = [risk.title for risk in risk.major_risks][:3]
        conditions = risk.mitigations if recommendation != CommitteeRecommendation.BUY else []
        report = InvestmentCommitteeReport(
            summary=InvestmentCommitteeSummary(
                state.company_name,
                recommendation,
                confidence,
                valuation.summary.fair_value_per_share,
                valuation.lbo_returns.irr if valuation.lbo_returns else None,
                (
                    f"Committee recommendation: {recommendation.value} "
                    f"{state.company_name}; support score {support_weight:.0%}."
                ),
            ),
            votes=votes,
            investment_thesis=[vote.rationale for vote in votes if vote.outcome == "SUPPORT"],
            top_risks=top_risks,
            conditions_precedent=conditions,
        )
        state.recommendation = {"report": report, "recommendation": recommendation.value}
        state.metadata["investment_committee_report"] = report
        return AgentResponse(
            self.name,
            report.summary.executive_summary,
            confidence,
            [vote.area for vote in votes],
            {"report": report},
        )

    @staticmethod
    def _recommendation(
        support_weight: float, irr: float, risk_level: str
    ) -> CommitteeRecommendation:
        if support_weight >= 0.75 and irr >= 0.20 and risk_level != "Critical":
            return CommitteeRecommendation.BUY
        if support_weight >= 0.45 and risk_level != "Critical":
            return CommitteeRecommendation.HOLD
        return CommitteeRecommendation.REJECT
