"""Deterministic scorecards behind each Investment Committee debate persona."""

from __future__ import annotations

from typing import Any

from .ic_simulation_models import (
    DealPartnerOpinion,
    DissentingView,
    OperatingPartnerOpinion,
    PartnerPosition,
    RiskOfficerOpinion,
    RiskOfficerVerdict,
    ValueCreationPotential,
)


def _scenario_outcome(valuation_report: Any, name: str) -> Any | None:
    analysis = getattr(valuation_report, "scenario_analysis", None)
    if analysis is None:
        return None
    return next((outcome for outcome in analysis.outcomes if outcome.name == name), None)


class DealPartnerTools:
    """Builds the bull case: the argument for doing the deal."""

    @staticmethod
    def required_reports(state: Any) -> tuple[Any, Any, Any]:
        reports = (
            state.metadata.get("financial_report"),
            state.metadata.get("valuation_report"),
            state.metadata.get("industry_report"),
        )
        if any(report is None for report in reports):
            raise ValueError("Deal Partner requires financial, valuation, and industry reports")
        return reports

    @staticmethod
    def evaluate(
        financial: Any, valuation: Any, industry: Any
    ) -> DealPartnerOpinion:
        irr = valuation.lbo_returns.irr if valuation.lbo_returns else 0.0
        health = financial.summary.health.value
        position = industry.summary.competitive_position.value
        upside = valuation.summary.upside_downside_pct

        thesis = [
            f"Base-case LBO IRR of {irr:.1%}.",
            f"Financial health rated {health}.",
            f"Competitive position is {position}.",
        ]
        if upside is not None:
            thesis.append(f"Implied upside of {upside:.1%} to fair value.")
        bull = _scenario_outcome(valuation, "Bull")
        if bull is not None:
            thesis.append(
                f"Bull case reaches {bull.irr:.1%} IRR at a {bull.exit_multiple:.1f}x exit."
            )

        if irr >= 0.20 and health in {"Excellent", "Good"} and position in {"Leader", "Strong"}:
            stance = PartnerPosition.ADVOCATE
        elif irr < 0.10 or health in {"Weak", "Distressed"}:
            stance = PartnerPosition.OPPOSE
        else:
            stance = PartnerPosition.NEUTRAL

        return DealPartnerOpinion(
            position=stance,
            thesis=thesis,
            rationale=(
                f"IRR {irr:.1%}, {health} financial health, and a {position} market position "
                f"support a {stance.value.lower()} stance."
            ),
        )


class RiskOfficerTools:
    """The skeptic: reviews risk, diligence, and the downside case for a veto-worthy issue."""

    @staticmethod
    def required_reports(state: Any) -> tuple[Any, Any, Any]:
        reports = (
            state.metadata.get("risk_report"),
            state.metadata.get("due_diligence_report"),
            state.metadata.get("valuation_report"),
        )
        if reports[0] is None or reports[1] is None:
            raise ValueError("Risk Officer requires risk and due diligence reports")
        return reports

    @staticmethod
    def evaluate(risk: Any, due_diligence: Any, valuation: Any | None) -> RiskOfficerOpinion:
        risk_level = risk.summary.level.value
        dd_assessment = due_diligence.summary.assessment.value
        bear = _scenario_outcome(valuation, "Bear") if valuation is not None else None
        bear_irr = bear.irr if bear is not None else None

        if dd_assessment == "Critical" or risk_level == "Critical" or (
            bear_irr is not None and bear_irr <= -0.50
        ):
            verdict = RiskOfficerVerdict.VETO
        elif risk_level == "High" or dd_assessment == "Caution" or (
            bear_irr is not None and bear_irr < 0.0
        ):
            verdict = RiskOfficerVerdict.CONDITIONAL
        else:
            verdict = RiskOfficerVerdict.CLEAR

        objections = [item.title for item in risk.major_risks] + [
            flag.title for flag in due_diligence.red_flags
        ]
        conditions = list(risk.mitigations) if verdict != RiskOfficerVerdict.CLEAR else []

        bear_text = f"; bear-case IRR is {bear_irr:.1%}" if bear_irr is not None else ""
        return RiskOfficerOpinion(
            verdict=verdict,
            objections=objections,
            required_conditions=conditions,
            rationale=(
                f"Aggregate risk is {risk_level}, due diligence assessment is {dd_assessment}"
                f"{bear_text}."
            ),
        )


class OperatingPartnerTools:
    """Assesses whether there is a credible operational value-creation path, not just leverage."""

    @staticmethod
    def required_reports(state: Any) -> tuple[Any, Any]:
        reports = (
            state.metadata.get("valuation_report"),
            state.metadata.get("industry_report"),
        )
        if any(report is None for report in reports):
            raise ValueError("Operating Partner requires valuation and industry reports")
        return reports

    @staticmethod
    def evaluate(valuation: Any, industry: Any) -> OperatingPartnerOpinion:
        base = _scenario_outcome(valuation, "Base")
        bull = _scenario_outcome(valuation, "Bull")
        spread = (bull.irr - base.irr) if (base is not None and bull is not None) else 0.0

        if spread >= 0.08:
            potential = ValueCreationPotential.STRONG
        elif spread >= 0.03:
            potential = ValueCreationPotential.MODERATE
        else:
            potential = ValueCreationPotential.LIMITED

        levers = list(industry.management_themes)
        levers.append(f"Bull-vs-base IRR spread of {spread:.1%} from operating upside.")

        return OperatingPartnerOpinion(
            potential=potential,
            value_levers=levers,
            rationale=(
                f"Bull-case outperformance over base case is {spread:.1%}, implying "
                f"{potential.value.lower()} value-creation potential beyond the base case."
            ),
        )


class ChairpersonTools:
    """Rules on a final recommendation from the committee vote and the three persona opinions."""

    @staticmethod
    def rule(
        committee_recommendation: str,
        deal_partner: DealPartnerOpinion,
        risk_officer: RiskOfficerOpinion,
        operating_partner: OperatingPartnerOpinion,
    ) -> tuple[str, list[DissentingView], str]:
        final = committee_recommendation

        if risk_officer.verdict == RiskOfficerVerdict.VETO:
            final = "REJECT"
        elif risk_officer.verdict == RiskOfficerVerdict.CONDITIONAL and final == "BUY":
            final = "HOLD"
        elif deal_partner.position == PartnerPosition.OPPOSE and final == "BUY":
            final = "HOLD"

        dissent: list[DissentingView] = []
        if deal_partner.position == PartnerPosition.ADVOCATE and final != "BUY":
            dissent.append(
                DissentingView("Deal Partner", "BUY", deal_partner.rationale)
            )
        if risk_officer.verdict == RiskOfficerVerdict.VETO and committee_recommendation == "BUY":
            dissent.append(
                DissentingView(
                    "Investment Committee scorecard", "BUY", "Overruled by Risk Officer veto."
                )
            )
        if operating_partner.potential == ValueCreationPotential.LIMITED and final == "BUY":
            dissent.append(
                DissentingView("Operating Partner", "HOLD", operating_partner.rationale)
            )

        rationale = (
            f"Committee scorecard recommended {committee_recommendation}; "
            f"Risk Officer verdict is {risk_officer.verdict.value}; "
            f"Deal Partner is {deal_partner.position.value.lower()}; "
            f"final ruling is {final}."
        )
        return final, dissent, rationale
