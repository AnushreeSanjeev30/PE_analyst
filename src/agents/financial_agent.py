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
    ) -> FinancialReport:

        ratios = analysis["ratios"]

        # The ratio engine returns ROE as a decimal (0.25 == 25%).
        roe = ratios.get("roe", 0)
        current_ratio = ratios.get(
            "current_ratio",
            0,
        )

        ############################################################

        if roe > 0.20:

            health = FinancialHealth.EXCELLENT

        elif roe > 0.15:

            health = FinancialHealth.GOOD

        elif roe > 0.10:

            health = FinancialHealth.AVERAGE

        else:

            health = FinancialHealth.WEAK

        ############################################################

        summary = FinancialSummary(

            company_name=company,

            health=health,

            trend=Trend.STABLE,

            confidence=0.90,

            executive_summary=(
                f"{company} demonstrates "
                f"{health.value.lower()} "
                "financial health based on "
                "profitability and liquidity."
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

        ############################################################

        strengths = []

        weaknesses = []

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

        recommendation = FinancialRecommendation(

            recommendation="Positive",

            reasoning=(
                "Company demonstrates healthy "
                "fundamental metrics."
            ),
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