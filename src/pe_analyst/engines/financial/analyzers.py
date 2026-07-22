"""
Financial analysis and quality-of-earnings analyzer.

This module interprets deterministic financial metrics and produces
human-readable findings that can later be consumed by AI agents.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .engine import FinancialAnalysisReport


class Severity(StrEnum):
    """Severity level for findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(slots=True, frozen=True)
class AnalysisFinding:
    """
    Represents one financial finding.
    """

    severity: Severity
    title: str
    description: str


@dataclass(slots=True)
class QualityOfEarningsReport:
    """
    Output of the Quality of Earnings Analyzer.
    """

    score: int
    findings: list[AnalysisFinding] = field(default_factory=list)

    @property
    def overall_rating(self) -> str:
        if self.score >= 85:
            return "Excellent"

        if self.score >= 70:
            return "Good"

        if self.score >= 55:
            return "Moderate"

        return "High Risk"


class QualityOfEarningsAnalyzer:
    """
    Rule-based analyzer for financial health.

    This analyzer is deterministic.
    No AI is used here.
    """

    def analyze(
        self,
        report: FinancialAnalysisReport,
    ) -> QualityOfEarningsReport:

        findings: list[AnalysisFinding] = []

        score = 100

        # ------------------------------
        # Liquidity
        # ------------------------------

        if report.current_ratio < 1:
            score -= 15

            findings.append(
                AnalysisFinding(
                    severity=Severity.HIGH,
                    title="Liquidity Risk",
                    description=(
                        "Current Ratio is below 1. "
                        "The company may struggle to meet "
                        "its short-term obligations."
                    ),
                )
            )

        elif report.current_ratio < 1.5:
            score -= 5

            findings.append(
                AnalysisFinding(
                    severity=Severity.MEDIUM,
                    title="Liquidity",
                    description="Current Ratio is adequate but could improve.",
                )
            )

        else:
            findings.append(
                AnalysisFinding(
                    severity=Severity.LOW,
                    title="Liquidity",
                    description="Healthy short-term liquidity.",
                )
            )

        # ------------------------------
        # Leverage
        # ------------------------------

        if report.debt_to_ebitda > 5:
            score -= 20

            findings.append(
                AnalysisFinding(
                    severity=Severity.HIGH,
                    title="High Leverage",
                    description=("Debt / EBITDA exceeds 5x. This may increase refinancing risk."),
                )
            )

        elif report.debt_to_ebitda > 3:
            score -= 8

            findings.append(
                AnalysisFinding(
                    severity=Severity.MEDIUM,
                    title="Leverage",
                    description="Debt level is moderately high.",
                )
            )

        else:
            findings.append(
                AnalysisFinding(
                    severity=Severity.LOW,
                    title="Leverage",
                    description="Debt level appears manageable.",
                )
            )

        # ------------------------------
        # Profitability
        # ------------------------------

        if report.ebitda_margin < 0.10:
            score -= 15

            findings.append(
                AnalysisFinding(
                    severity=Severity.HIGH,
                    title="Weak Profitability",
                    description="EBITDA Margin is below 10%.",
                )
            )

        elif report.ebitda_margin < 0.20:
            score -= 5

            findings.append(
                AnalysisFinding(
                    severity=Severity.MEDIUM,
                    title="Profitability",
                    description="EBITDA Margin is average.",
                )
            )

        else:
            findings.append(
                AnalysisFinding(
                    severity=Severity.LOW,
                    title="Profitability",
                    description="Strong EBITDA Margin.",
                )
            )

        # ------------------------------
        # Revenue Growth
        # ------------------------------

        if report.revenue_growth < 0:
            score -= 10

            findings.append(
                AnalysisFinding(
                    severity=Severity.HIGH,
                    title="Revenue Decline",
                    description="Revenue decreased compared to the previous period.",
                )
            )

        elif report.revenue_growth < 0.05:
            score -= 3

            findings.append(
                AnalysisFinding(
                    severity=Severity.MEDIUM,
                    title="Slow Growth",
                    description="Revenue growth is below 5%.",
                )
            )

        else:
            findings.append(
                AnalysisFinding(
                    severity=Severity.LOW,
                    title="Revenue Growth",
                    description="Healthy revenue growth.",
                )
            )

        # ------------------------------
        # Earnings Growth
        # ------------------------------

        if report.earnings_growth < 0:
            score -= 12

            findings.append(
                AnalysisFinding(
                    severity=Severity.HIGH,
                    title="Declining Earnings",
                    description="Net income decreased year-over-year.",
                )
            )

        else:
            findings.append(
                AnalysisFinding(
                    severity=Severity.LOW,
                    title="Earnings",
                    description="Net income is improving.",
                )
            )

        score = max(score, 0)

        return QualityOfEarningsReport(
            score=score,
            findings=findings,
        )
