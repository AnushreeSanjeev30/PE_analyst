"""
financial_tools.py

Tools used by the Financial Agent.

This module acts as a bridge between the deterministic
financial engines and the AI agents.

The Financial Agent NEVER performs calculations itself.
Instead, it calls these tools.
"""

from dataclasses import asdict
from typing import Any

# Use the project's financial engine package
from pe_analyst.engines.financial import (
    FinancialAnalysisEngine,
    QualityOfEarningsAnalyzer,
)


class FinancialTools:
    """
    Collection of deterministic financial tools.
    """

    def __init__(self) -> None:

        self.analysis_engine = FinancialAnalysisEngine()

        self.quality_engine = QualityOfEarningsAnalyzer()

    ##################################################################
    # Financial Ratios
    ##################################################################

    def calculate_ratios(
        self,
        financials: Any,
    ) -> dict[str, Any]:

        # Expect `financials` to be a dict with `current` and `previous`
        if isinstance(financials, dict) and {
            "current",
            "previous",
        }.issubset(financials.keys()):

            report = self.analysis_engine.analyze(
                current=financials["current"],
                previous=financials["previous"],
            )

        else:
            raise TypeError(
                "financials must be a dict containing 'current' and "
                "'previous' FinancialStatement objects"
            )

        return asdict(report)

    ##################################################################
    # Quality Analysis
    ##################################################################

    def quality_analysis(
        self,
        financials: Any,
    ) -> dict[str, Any]:

        # Reuse the analysis engine to produce a FinancialAnalysisReport
        if isinstance(financials, dict) and {
            "current",
            "previous",
        }.issubset(financials.keys()):

            report = self.analysis_engine.analyze(
                current=financials["current"],
                previous=financials["previous"],
            )

        else:
            raise TypeError(
                "financials must be a dict containing 'current' and "
                "'previous' FinancialStatement objects"
            )

        quality = self.quality_engine.analyze(report)

        return asdict(quality)

    ##################################################################
    # Complete Analysis
    ##################################################################

    def full_analysis(
        self,
        financials: Any,
    ) -> dict[str, Any]:

        ratios = self.calculate_ratios(
            financials
        )

        quality = self.quality_analysis(
            financials
        )

        return {
            "ratios": ratios,
            "quality": quality,
        }

    ##################################################################
    # Convenience
    ##################################################################

    def get_metric(
        self,
        financials: Any,
        metric_name: str,
    ) -> Any:

        ratios = self.calculate_ratios(
            financials
        )

        return ratios.get(metric_name)