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
