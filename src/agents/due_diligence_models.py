"""Evidence-grounded red-flag detection output models for the Due Diligence Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from .industry_models import SourceCitation


class RedFlagSeverity(StrEnum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


class DueDiligenceAssessment(StrEnum):
    CLEAR = "Clear"
    CAUTION = "Caution"
    CRITICAL = "Critical"


@dataclass(slots=True)
class RedFlag:
    title: str
    category: str
    severity: RedFlagSeverity
    rationale: str
    citation: SourceCitation


@dataclass(slots=True)
class DueDiligenceSummary:
    company_name: str
    assessment: DueDiligenceAssessment
    red_flag_count: int
    confidence: float
    executive_summary: str


@dataclass(slots=True)
class DueDiligenceReport:
    summary: DueDiligenceSummary
    red_flags: list[RedFlag] = field(default_factory=list)
    items_reviewed: int = 0
