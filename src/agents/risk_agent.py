"""Transparent risk agent for private-equity underwriting."""

from __future__ import annotations

from .base_agent import BaseAgent
from .risk_models import RiskItem, RiskLevel, RiskReport, RiskSummary
from .risk_tools import RiskTools
from .state import AgentState
from .types import AgentResponse


class RiskAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__("Risk Agent")
        self.tools = RiskTools()

    def execute(self, state: AgentState) -> AgentResponse:
        factors, missing = self.tools.evaluate(state)
        if not factors:
            raise ValueError(
                "Risk analysis requires at least one financial, valuation, or industry metric"
            )
        score = sum(factor.score for factor in factors) / len(factors)
        level = self.tools.level(score)
        confidence = max(0.30, min(0.95, 0.95 - (0.07 * len(missing))))
        major_risks = [
            RiskItem(
                title=f"{factor.category} risk",
                description=factor.rationale,
                severity=factor.level,
                mitigation=self._mitigation(factor.category),
            )
            for factor in factors
            if factor.level in {RiskLevel.HIGH, RiskLevel.CRITICAL}
        ]
        report = RiskReport(
            summary=RiskSummary(
                state.company_name,
                score,
                level,
                confidence,
                f"{state.company_name} has a {level.value.lower()} risk score of {score:.0f}/100.",
            ),
            factors=factors,
            major_risks=major_risks,
            mitigations=[risk.mitigation for risk in major_risks],
            missing_data=missing,
        )
        state.risk = {"report": report, "score": score, "level": level.value}
        state.metadata["risk_report"] = report
        return AgentResponse(
            self.name,
            report.summary.executive_summary,
            confidence,
            [item.title for item in major_risks],
            {"report": report},
        )

    @staticmethod
    def _mitigation(category: str) -> str:
        return {
            "Liquidity": "Require a minimum liquidity reserve and monthly cash forecast.",
            "Leverage": "Reduce entry leverage or mandate a cash-sweep deleveraging plan.",
            "Interest Coverage": "Stress-test base rates and require covenant headroom.",
            "Cash Flow": "Validate working-capital and capex assumptions through diligence.",
            "Valuation": "Lower the entry valuation or require a higher return hurdle.",
            "Industry": "Complete market diligence and downside case analysis.",
        }.get(category, "Validate the metric during confirmatory diligence.")
