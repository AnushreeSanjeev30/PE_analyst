"""Evidence-grounded output models for the Industry Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class CompetitivePosition(StrEnum):
    LEADER = "Leader"
    STRONG = "Strong"
    NEUTRAL = "Neutral"
    WEAK = "Weak"


@dataclass(slots=True)
class SourceCitation:
    source: str
    page_number: int
    excerpt: str
    confidence: float


@dataclass(slots=True)
class IndustryFinding:
    title: str
    analysis: str
    citations: list[SourceCitation] = field(default_factory=list)


@dataclass(slots=True)
class CompetitorProfile:
    name: str
    market_share_pct: float | None = None
    positioning: str = ""


@dataclass(slots=True)
class IndustrySummary:
    industry_name: str
    market_growth_pct: float | None
    competitive_position: CompetitivePosition
    confidence: float
    executive_summary: str


@dataclass(slots=True)
class IndustryReport:
    summary: IndustrySummary
    competitors: list[CompetitorProfile] = field(default_factory=list)
    findings: list[IndustryFinding] = field(default_factory=list)
    porter_forces: dict[str, int] = field(default_factory=dict)
    management_themes: list[str] = field(default_factory=list)
    evidence_count: int = 0
