"""Deterministic, rule-based multi-agent Investment Committee debate.

``InvestmentCommitteeAgent`` already produces a weighted-vote scorecard from the specialist
reports. These models back a genuine debate layered on top of that scorecard: three committee
personas (Deal Partner, Risk Officer, Operating Partner) each form an independent, rule-based
opinion from the same specialist reports, and the Chairperson rules on a final recommendation --
with explicit veto power for the Risk Officer and a recorded dissent trail, same as a real IC.
No LLM is involved; every rule is fixed and reproducible, matching the rest of the agent stack.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .industry_models import SourceCitation
from .investment_models import InvestmentCommitteeReport


class PartnerPosition(StrEnum):
    ADVOCATE = "Advocate"
    NEUTRAL = "Neutral"
    OPPOSE = "Oppose"


@dataclass(slots=True)
class DealPartnerOpinion:
    position: PartnerPosition
    thesis: list[str]
    rationale: str


class RiskOfficerVerdict(StrEnum):
    CLEAR = "Clear"
    CONDITIONAL = "Conditional"
    VETO = "Veto"


@dataclass(slots=True)
class RiskOfficerOpinion:
    verdict: RiskOfficerVerdict
    objections: list[str]
    required_conditions: list[str]
    rationale: str


class ValueCreationPotential(StrEnum):
    STRONG = "Strong"
    MODERATE = "Moderate"
    LIMITED = "Limited"


@dataclass(slots=True)
class OperatingPartnerOpinion:
    potential: ValueCreationPotential
    value_levers: list[str]
    rationale: str


@dataclass(slots=True)
class DissentingView:
    member: str
    position: str
    rationale: str


class DriverDirection(StrEnum):
    SUPPORTS = "Supports"
    AGAINST = "Against"


@dataclass(slots=True)
class DecisionDriver:
    """One factor behind the ruling, with what it rests on and the passages that back it."""

    area: str
    direction: DriverDirection
    weight: float | None
    statement: str
    # "Document evidence" | "Calculated" | "Analyst input" -- see agents.decision_explanation.
    basis: str
    basis_detail: str
    evidence: list[SourceCitation] = field(default_factory=list)


@dataclass(slots=True)
class DecisionExplanation:
    """Why the committee ruled the way it did, traceable to the source document."""

    recommendation: str
    headline: str
    deciding_rule: str
    support_weight: float
    drivers: list[DecisionDriver] = field(default_factory=list)
    conditions: list[str] = field(default_factory=list)
    what_would_change: list[str] = field(default_factory=list)
    evidence_gaps: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ICDecision:
    company_name: str
    final_recommendation: str
    unanimous: bool
    chair_rationale: str
    committee_vote: InvestmentCommitteeReport
    deal_partner: DealPartnerOpinion
    risk_officer: RiskOfficerOpinion
    operating_partner: OperatingPartnerOpinion
    dissent: list[DissentingView] = field(default_factory=list)
    explanation: DecisionExplanation | None = None
