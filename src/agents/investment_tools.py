"""Deterministic decision rules for investment-committee recommendations."""

from __future__ import annotations

from typing import Any

from .investment_models import CommitteeVote


class InvestmentTools:
    """Converts specialist-agent reports into a visible committee decision trace."""

    @staticmethod
    def required_reports(state: Any) -> tuple[Any, Any, Any, Any, Any]:
        reports = (
            state.metadata.get("financial_report"),
            state.metadata.get("valuation_report"),
            state.metadata.get("risk_report"),
            state.metadata.get("industry_report"),
            state.metadata.get("due_diligence_report"),
        )
        if any(report is None for report in reports):
            raise ValueError(
                "Investment Committee requires financial, valuation, risk, industry, "
                "and due diligence reports"
            )
        return reports

    @staticmethod
    def vote_financial(report: Any) -> CommitteeVote:
        health = report.summary.health.value
        favorable = health in {"Excellent", "Good"}
        return CommitteeVote(
            "Financial health",
            "SUPPORT" if favorable else "CONCERN",
            f"Financial health is {health}.",
            0.15,
        )

    @staticmethod
    def vote_valuation(report: Any) -> CommitteeVote:
        irr = report.lbo_returns.irr if report.lbo_returns else 0.0
        upside = report.summary.upside_downside_pct
        favorable = irr >= 0.20 and (upside is None or upside >= 0.15)
        upside_text = "not provided" if upside is None else f"{upside:.1%}"
        return CommitteeVote(
            "Valuation",
            "SUPPORT" if favorable else "CONCERN",
            f"Base-case LBO IRR is {irr:.1%}; upside is {upside_text}.",
            0.35,
        )

    @staticmethod
    def vote_risk(report: Any) -> CommitteeVote:
        level = report.summary.level.value
        favorable = level in {"Low", "Moderate"}
        return CommitteeVote(
            "Risk",
            "SUPPORT" if favorable else "CONCERN",
            f"Aggregate risk is {level} ({report.summary.score:.0f}/100).",
            0.20,
        )

    @staticmethod
    def vote_industry(report: Any) -> CommitteeVote:
        position = report.summary.competitive_position.value
        favorable = position in {"Leader", "Strong"}
        return CommitteeVote(
            "Industry",
            "SUPPORT" if favorable else "CONCERN",
            f"Competitive position is {position}.",
            0.10,
        )

    @staticmethod
    def vote_due_diligence(report: Any) -> CommitteeVote:
        assessment = report.summary.assessment.value
        favorable = assessment == "Clear"
        return CommitteeVote(
            "Due diligence",
            "SUPPORT" if favorable else "CONCERN",
            f"Due diligence assessment is {assessment} "
            f"({report.summary.red_flag_count} red flag(s)).",
            0.20,
        )
