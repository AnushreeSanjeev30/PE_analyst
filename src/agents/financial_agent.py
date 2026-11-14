"""
financial_agent.py

Financial Agent

This agent is responsible for:

1. Running deterministic financial analysis.
2. Interpreting the results.
3. Updating the shared AgentState.
"""

from __future__ import annotations

from typing import Any

from .base_agent import BaseAgent
from .financial_models import (
    FinancialFinding,
    FinancialHealth,
    FinancialRecommendation,
    FinancialReport,
    FinancialStrength,
    FinancialSummary,
    FinancialWeakness,
    MetricScore,
    Trend,
)
from .financial_tools import FinancialTools
from .state import AgentState
from .types import AgentResponse


class FinancialAgent(BaseAgent):

    def __init__(self) -> None:

        super().__init__("Financial Agent")

        self.tools = FinancialTools()

    ####################################################################
    # Main Logic
    ####################################################################

    def execute(
        self,
        state: AgentState,
    ) -> AgentResponse:

        financials = state.financial_data

        analysis = self.tools.full_analysis(financials)

        report = self.generate_report(
            state.company_name,
            analysis,
            financials.get("current") if isinstance(financials, dict) else None,
        )

        state.ratios = analysis["ratios"]
        state.quality = analysis["quality"]
        state.metadata["financial_report"] = report

        return AgentResponse(
            agent_name=self.name,
            summary=report.summary.executive_summary,
            confidence=report.summary.confidence,
            findings=[
                finding.title
                for finding in report.findings
            ],
            metadata={
                "report": report
            },
        )

    ####################################################################
    # Report Generator
    ####################################################################

    def generate_report(
        self,
        company: str,
        analysis: dict[str, Any],
        current: Any | None = None,
    ) -> FinancialReport:
        """Rate financial health from the ratios, checking for distress first.

        ``current`` is the current-period statement. It is needed because return on equity
        alone is misleading for a troubled company: a net loss divided by negative equity is a
        *positive* ROE, which used to rate an insolvent business "Excellent".
        """

        ratios = analysis["ratios"]

        # The ratio engine returns ROE as a decimal (0.25 == 25%).
        roe = ratios.get("roe", 0)
        current_ratio = ratios.get(
            "current_ratio",
            0,
        )

        distress = self._distress_signals(current)
        negative_equity = current is not None and current.shareholders_equity <= 0
        loss_making = current is not None and current.net_income < 0

        ############################################################

        if distress:

            health = FinancialHealth.DISTRESSED

        elif loss_making:

            health = FinancialHealth.WEAK

        elif roe > 0.20:

            health = FinancialHealth.EXCELLENT

        elif roe > 0.15:

            health = FinancialHealth.GOOD

        elif roe > 0.10:

            health = FinancialHealth.AVERAGE

        else:

            health = FinancialHealth.WEAK

        ############################################################

        if distress:
            basis = " ".join(distress)
        elif loss_making:
            basis = "The company made a net loss in the current period."
        else:
            basis = f"Return on equity is {roe:.1%} and the current ratio is {current_ratio:.2f}."

        summary = FinancialSummary(

            company_name=company,

            health=health,

            trend=Trend.STABLE,

            confidence=0.90,

            executive_summary=(
                f"{company} demonstrates "
                f"{health.value.lower()} "
                f"financial health. {basis}"
            ),
        )

        ############################################################

        metrics = [

            MetricScore(

                name="ROE",

                value=roe * 100,

                benchmark=15,

                unit="%",

            ),

            MetricScore(

                name="Current Ratio",

                value=current_ratio,

                benchmark=1.5,

            ),
        ]

        ############################################################

        findings = [

            FinancialFinding(

                title="Financial Analysis Completed",

                description=(
                    "Financial ratios successfully "
                    "computed."
                ),
            )
        ]

        if negative_equity:

            findings.append(

                FinancialFinding(

                    title="ROE is not meaningful",

                    description=(
                        "Shareholders' equity is zero or negative, so return on equity "
                        "cannot be read as a measure of profitability and was not used "
                        "to rate financial health."
                    ),

                    severity="WARNING",
                )
            )

        ############################################################

        strengths = []

        weaknesses = []

        if negative_equity:

            weaknesses.append(

                FinancialWeakness(

                    title="Negative shareholders' equity",

                    explanation=(
                        "Liabilities exceed assets; accumulated losses have wiped out "
                        "the equity base."
                    ),
                )
            )

        if loss_making:

            weaknesses.append(

                FinancialWeakness(

                    title="Net loss",

                    explanation=(
                        "The company lost money in the current period."
                    ),
                )
            )

        if current is not None and current.ebit < current.interest_expense:

            weaknesses.append(

                FinancialWeakness(

                    title="Operating profit does not cover interest",

                    explanation=(
                        "EBIT is below interest expense, so debt is being serviced "
                        "from cash reserves or new borrowing."
                    ),
                )
            )

        if not negative_equity and not loss_making:

            if roe > 0.20:

                strengths.append(

                    FinancialStrength(

                        title="Strong Profitability",

                        explanation=(
                            "ROE exceeds industry "
                            "benchmark."
                        ),
                    )
                )

            else:

                weaknesses.append(

                    FinancialWeakness(

                        title="Low Profitability",

                        explanation=(
                            "ROE below preferred "
                            "benchmark."
                        ),
                    )
                )

        ############################################################

        if health in {FinancialHealth.EXCELLENT, FinancialHealth.GOOD}:

            recommendation = FinancialRecommendation(

                recommendation="Positive",

                reasoning=(
                    "Company demonstrates healthy "
                    "fundamental metrics."
                ),
            )

        elif health == FinancialHealth.AVERAGE:

            recommendation = FinancialRecommendation(

                recommendation="Neutral",

                reasoning=(
                    "Profitability is adequate but below the preferred benchmark."
                ),
            )

        else:

            recommendation = FinancialRecommendation(

                recommendation="Negative",

                reasoning=basis,
            )

        ############################################################

        return FinancialReport(

            summary=summary,

            findings=findings,

            metrics=metrics,

            strengths=strengths,

            weaknesses=weaknesses,

            recommendation=recommendation,
        )

    @staticmethod
    def _distress_signals(current: Any | None) -> list[str]:
        """Reasons the company counts as financially distressed; empty when it does not.

        Either signal is enough: equity at or below zero (technically insolvent on the balance
        sheet), or a net loss while operating profit fails to cover interest (losing money and
        unable to service its debt from operations).
        """

        if current is None:
            return []
        signals: list[str] = []
        if current.shareholders_equity <= 0:
            signals.append("Shareholders' equity is zero or negative.")
        if current.net_income < 0 and current.ebit < current.interest_expense:
            signals.append(
                "The company made a net loss and operating profit does not cover interest."
            )
        return signals
