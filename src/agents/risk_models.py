"""Typed, reviewable output models for the private-equity Risk Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class RiskLevel(StrEnum):
    LOW = "Low"
    MODERATE = "Moderate"
    HIGH = "High"
    CRITICAL = "Critical"


@dataclass(slots=True)
class RiskFactor:
    category: str
    score: float
    level: RiskLevel
    rationale: str
    metric: float | None = None
    benchmark: float | None = None


@dataclass(slots=True)
class RiskItem:
    title: str
    description: str
    severity: RiskLevel
    mitigation: str


@dataclass(slots=True)
class RiskSummary:
    company_name: str
    score: float
    level: RiskLevel
    confidence: float
    executive_summary: str


@dataclass(slots=True)
class RiskReport:
    summary: RiskSummary
    factors: list[RiskFactor] = field(default_factory=list)
    major_risks: list[RiskItem] = field(default_factory=list)
    mitigations: list[str] = field(default_factory=list)
    missing_data: list[str] = field(default_factory=list)
