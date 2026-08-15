"""Typed investment-committee output contracts."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CommitteeRecommendation(StrEnum):
    BUY = "BUY"
    HOLD = "HOLD"
    REJECT = "REJECT"


@dataclass(slots=True)
class CommitteeVote:
    area: str
    outcome: str
    rationale: str
    weight: float


@dataclass(slots=True)
class InvestmentCommitteeSummary:
    company_name: str
    recommendation: CommitteeRecommendation
    confidence: float
    target_price: float | None
    expected_irr: float | None
    executive_summary: str


@dataclass(slots=True)
class InvestmentCommitteeReport:
    summary: InvestmentCommitteeSummary
    votes: list[CommitteeVote] = field(default_factory=list)
    investment_thesis: list[str] = field(default_factory=list)
    top_risks: list[str] = field(default_factory=list)
    conditions_precedent: list[str] = field(default_factory=list)
