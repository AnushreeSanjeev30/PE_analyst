"""Builds the "why" behind an Investment Committee ruling.

A BUY / HOLD / REJECT on its own is not usable by a deal team: they need to see which factors
drove it, how much each one weighed, what in the source document backs each factor, and what
would have to be true for the answer to change. ``build_decision_explanation`` assembles that
from reports the specialist agents already produced. It makes no new judgements and calls no
LLM; every sentence restates a rule that fired or quotes cited evidence, so the explanation
can never disagree with the decision it explains.

Each driver also says what its conclusion rests on, because a number computed from the
document, an assumption the analyst typed in and a quoted passage deserve different levels of
trust:

* ``Document evidence``      -- quoted passages with a page number.
* ``Calculated``             -- produced by a deterministic engine from the inputs.
* ``Analyst input``          -- supplied by the person who ran the analysis.
"""

from __future__ import annotations

from typing import Any

from .ic_simulation_models import (
    DealPartnerOpinion,
    DecisionDriver,
    DecisionExplanation,
    DriverDirection,
    OperatingPartnerOpinion,
    PartnerPosition,
    RiskOfficerOpinion,
    RiskOfficerVerdict,
)
from .ic_simulation_tools import ChairpersonTools
from .industry_models import SourceCitation
from .investment_models import CommitteeVote, InvestmentCommitteeReport

BASIS_DOCUMENT = "Document evidence"
BASIS_CALCULATED = "Calculated"
BASIS_ANALYST = "Analyst input"

_MAX_CITATIONS_PER_DRIVER = 5
_MAX_DETAIL_CHARS = 220

# What each scorecard area needs in order to count as support. These restate the rules in
# ``InvestmentTools`` and ``DueDiligenceAgent``; keep them in step if those thresholds move.
_SUPPORT_CONDITIONS = {
    "Financial health": "Financial health rated Good or Excellent.",
    "Valuation": (
        "Base-case LBO IRR of at least 20%, with at least 15% upside to fair value when a "
        "current price is supplied."
    ),
    "Risk": "Aggregate risk rated Low or Moderate.",
    "Industry": "Competitive position rated Strong or Leader.",
    "Due diligence": "No red flag of Moderate severity or above in the reviewed material.",
}

_SEVERITY_ORDER = {"Critical": 0, "High": 1, "Moderate": 2, "Low": 3}

# Financial statement fields worth citing for the financial-health driver, most telling first.
_KEY_FINANCIAL_FIELDS = (
    "revenue",
    "ebitda",
    "net_income",
    "operating_cash_flow",
    "total_debt",
    "interest_expense",
)


def _clean(text: str, limit: int | None = None) -> str:
    """Collapse the line breaks PDF extraction leaves behind; optionally shorten."""

    flat = " ".join(str(text).split())
    if limit is not None and len(flat) > limit:
        return flat[: limit - 1].rstrip() + "..."
    return flat


def _statement(*parts: str) -> str:
    return " ".join(_clean(part) for part in parts if part)


def _citation(item: Any) -> SourceCitation:
    if isinstance(item, SourceCitation):
        return item
    return SourceCitation(
        str(item["source"]),
        int(item["page_number"]),
        str(item["excerpt"]),
        float(item["confidence"]),
        item.get("document_id"),
    )


def _dedupe(citations: list[SourceCitation]) -> list[SourceCitation]:
    seen: set[tuple[str, int, str]] = set()
    unique: list[SourceCitation] = []
    for citation in citations:
        key = (citation.source, citation.page_number, citation.excerpt)
        if key not in seen:
            seen.add(key)
            unique.append(citation)
    return unique[:_MAX_CITATIONS_PER_DRIVER]


def _direction(vote: CommitteeVote) -> DriverDirection:
    return DriverDirection.SUPPORTS if vote.outcome == "SUPPORT" else DriverDirection.AGAINST


def _financial_driver(
    vote: CommitteeVote, financial: Any, financial_evidence: list[dict[str, Any]]
) -> DecisionDriver:
    by_field = {str(item.get("field")): item for item in financial_evidence}
    citations = [
        _citation(by_field[name]) for name in _KEY_FINANCIAL_FIELDS if name in by_field
    ]
    details = [f"Strength: {item.title}." for item in financial.strengths[:2]]
    details += [f"Weakness: {item.title}." for item in financial.weaknesses[:2]]
    if citations:
        basis = BASIS_CALCULATED
        basis_detail = (
            "Ratios calculated from the financial statements extracted from the document; the "
            "source lines are cited below."
        )
    else:
        basis = BASIS_ANALYST
        basis_detail = (
            "Ratios calculated from financial statements typed in for this run. They are not "
            "traced to a document, so check them against the source accounts."
        )
    return DecisionDriver(
        area=vote.area,
        direction=_direction(vote),
        weight=vote.weight,
        statement=_statement(vote.rationale, *details),
        basis=basis,
        basis_detail=basis_detail,
        evidence=_dedupe(citations),
    )


def _valuation_driver(vote: CommitteeVote, valuation: Any) -> DecisionDriver:
    details = [
        f"{method.name} values the equity at {method.value_per_share:,.2f} per share "
        f"({method.weight:.0%} weight)."
        for method in valuation.methods
        if method.value_per_share is not None
    ]
    return DecisionDriver(
        area=vote.area,
        direction=_direction(vote),
        weight=vote.weight,
        statement=_statement(vote.rationale, *details),
        basis=BASIS_CALCULATED,
        basis_detail=(
            "Produced by the DCF, comparables and LBO engines from the valuation assumptions "
            "entered for this run (growth, margins, purchase price, exit multiple, peers). "
            "The result is only as good as those assumptions."
        ),
    )


def _risk_driver(vote: CommitteeVote, risk: Any) -> DecisionDriver:
    details = [
        f"{item.title} ({item.severity.value}): {item.description}"
        for item in risk.major_risks[:3]
    ]
    return DecisionDriver(
        area=vote.area,
        direction=_direction(vote),
        weight=vote.weight,
        statement=_statement(vote.rationale, *details),
        basis=BASIS_CALCULATED,
        basis_detail=(
            "Risk score calculated from the financial statements, the valuation results and "
            "any risk inputs supplied (Altman Z, Piotroski score, industry risk score)."
        ),
    )


def _industry_driver(vote: CommitteeVote, industry: Any) -> DecisionDriver:
    citations = [
        citation for finding in industry.findings for citation in finding.citations
    ]
    findings = [
        f"{finding.title}: {_clean(finding.analysis, _MAX_DETAIL_CHARS)}"
        for finding in industry.findings
        if finding.citations
    ]
    return DecisionDriver(
        area=vote.area,
        direction=_direction(vote),
        weight=vote.weight,
        statement=_statement(vote.rationale, *findings),
        basis=BASIS_DOCUMENT if citations else BASIS_ANALYST,
        basis_detail=(
            f"Based on {industry.evidence_count} cited excerpt(s) on market, competition and "
            "management. The competitive-position rating itself is an input to the run."
        ),
        evidence=_dedupe(citations),
    )


def _due_diligence_driver(vote: CommitteeVote, due_diligence: Any) -> DecisionDriver:
    flags = sorted(
        due_diligence.red_flags, key=lambda flag: _SEVERITY_ORDER.get(flag.severity.value, 9)
    )
    details = [
        f"{_clean(flag.title, _MAX_DETAIL_CHARS)} ({flag.severity.value})." for flag in flags[:5]
    ]
    if due_diligence.items_reviewed == 0:
        basis_detail = (
            "No diligence material was supplied, so nothing was reviewed. The absence of red "
            "flags here is not a clean bill of health."
        )
    else:
        basis_detail = (
            f"{due_diligence.items_reviewed} risk factor(s) and note(s) from the document were "
            "screened against fixed red-flag terms (for example going concern, litigation, "
            "customer concentration). Each flag quotes the passage that triggered it."
        )
    return DecisionDriver(
        area=vote.area,
        direction=_direction(vote),
        weight=vote.weight,
        statement=_statement(vote.rationale, *details),
        basis=BASIS_DOCUMENT,
        basis_detail=basis_detail,
        evidence=_dedupe([flag.citation for flag in flags]),
    )


def _conditions(risk_officer: RiskOfficerOpinion) -> list[str]:
    """What must be settled before signing.

    The Risk Officer's own conditions when there are any; otherwise, for a conditional or
    vetoed deal, each open objection becomes something to resolve -- a conditional approval
    with no stated conditions would leave the deal team with nothing to act on.
    """

    conditions = [_clean(item) for item in risk_officer.required_conditions]
    if not conditions and risk_officer.verdict != RiskOfficerVerdict.CLEAR:
        conditions = [
            f"Resolve or price in: {_clean(item, _MAX_DETAIL_CHARS)}"
            for item in risk_officer.objections
        ]
    return list(dict.fromkeys(conditions))


def _what_would_change(
    final: str,
    votes: list[CommitteeVote],
    risk_officer: RiskOfficerOpinion,
    deal_partner: DealPartnerOpinion,
) -> list[str]:
    if final == "BUY":
        return [
            "A Critical due diligence finding or Critical aggregate risk would trigger a Risk "
            "Officer veto and turn this into a REJECT.",
            "A bear-case IRR below zero, High aggregate risk or any new red flag would make the "
            "Risk Officer's approval conditional and cap the ruling at HOLD.",
        ]

    changes = [
        f"{vote.area} (weight {vote.weight:.0%}) would count as support with: "
        f"{_SUPPORT_CONDITIONS.get(vote.area, 'a favourable assessment.')}"
        for vote in votes
        if vote.outcome != "SUPPORT"
    ]
    if risk_officer.verdict == RiskOfficerVerdict.VETO:
        changes.append(
            "The Risk Officer veto must be lifted first: it stands while due diligence or "
            "aggregate risk is Critical, or the bear case loses half the equity or more."
        )
    elif risk_officer.verdict == RiskOfficerVerdict.CONDITIONAL:
        changes.append(
            "The Risk Officer's conditions must be met; until then a BUY is capped at HOLD."
        )
    if deal_partner.position == PartnerPosition.OPPOSE:
        changes.append(
            "The Deal Partner opposes while base-case IRR is under 10% or financial health is "
            "Weak or Distressed."
        )
    changes.append(
        "A BUY needs at least 75% of the scorecard weight in support and a base-case IRR of "
        "20% or more; a HOLD needs at least 45%."
    )
    return changes


def _evidence_gaps(
    risk: Any,
    industry: Any,
    due_diligence: Any,
    financial_evidence: list[dict[str, Any]],
) -> list[str]:
    gaps = [f"Risk analysis is missing: {item}" for item in risk.missing_data]
    if not financial_evidence:
        gaps.append(
            "Financial statements were entered by hand and are not traced to a document page."
        )
    if due_diligence.items_reviewed == 0:
        gaps.append("No due diligence material was reviewed.")
    if industry.evidence_count < 3:
        gaps.append(
            f"The industry view rests on only {industry.evidence_count} cited excerpt(s)."
        )
    low_confidence = [
        flag.title for flag in due_diligence.red_flags if flag.citation.confidence < 0.6
    ]
    if low_confidence:
        gaps.append(
            "Low extraction confidence on: " + ", ".join(low_confidence) + ". Read the cited "
            "page before relying on it."
        )
    return gaps


def build_decision_explanation(
    metadata: dict[str, Any],
    committee: InvestmentCommitteeReport,
    deal_partner: DealPartnerOpinion,
    risk_officer: RiskOfficerOpinion,
    operating_partner: OperatingPartnerOpinion,
    final: str,
) -> DecisionExplanation:
    """Explain ``final`` from the specialist reports held in the workflow ``metadata``."""

    financial = metadata["financial_report"]
    valuation = metadata["valuation_report"]
    risk = metadata["risk_report"]
    industry = metadata["industry_report"]
    due_diligence = metadata["due_diligence_report"]
    financial_evidence: list[dict[str, Any]] = metadata.get("financial_evidence") or []

    builders = {
        "Financial health": lambda vote: _financial_driver(vote, financial, financial_evidence),
        "Valuation": lambda vote: _valuation_driver(vote, valuation),
        "Risk": lambda vote: _risk_driver(vote, risk),
        "Industry": lambda vote: _industry_driver(vote, industry),
        "Due diligence": lambda vote: _due_diligence_driver(vote, due_diligence),
    }
    drivers = [
        builders[vote.area](vote)
        if vote.area in builders
        else DecisionDriver(
            vote.area, _direction(vote), vote.weight, vote.rationale, BASIS_CALCULATED, ""
        )
        for vote in committee.votes
    ]
    # Lead with what hurt the deal most, then what helped most.
    drivers.sort(
        key=lambda driver: (driver.direction != DriverDirection.AGAINST, -(driver.weight or 0.0))
    )

    supporting = [vote for vote in committee.votes if vote.outcome == "SUPPORT"]
    support_weight = sum(vote.weight for vote in supporting)
    scorecard = committee.summary.recommendation.value
    deciding_rule = ChairpersonTools.deciding_rule(scorecard, deal_partner, risk_officer)

    headline = (
        f"{final}. {len(supporting)} of {len(committee.votes)} scorecard areas support the "
        f"deal, carrying {support_weight:.0%} of the weight. {deciding_rule}"
    )

    return DecisionExplanation(
        recommendation=final,
        headline=headline,
        deciding_rule=deciding_rule,
        support_weight=support_weight,
        drivers=drivers,
        conditions=_conditions(risk_officer),
        what_would_change=_what_would_change(
            final, committee.votes, risk_officer, deal_partner
        ),
        evidence_gaps=_evidence_gaps(risk, industry, due_diligence, financial_evidence),
    )


__all__ = [
    "BASIS_ANALYST",
    "BASIS_CALCULATED",
    "BASIS_DOCUMENT",
    "build_decision_explanation",
]
