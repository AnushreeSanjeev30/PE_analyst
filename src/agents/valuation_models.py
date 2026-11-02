"""Typed, auditable output contracts for the Valuation Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ValuationRecommendation(StrEnum):
    ACCEPT = "Accept"
    WATCH = "Watch"
    REJECT = "Reject"
    INSUFFICIENT_DATA = "Insufficient Data"


@dataclass(slots=True)
class ValuationMethod:
    name: str
    enterprise_value: float | None = None
    equity_value: float | None = None
    value_per_share: float | None = None
    weight: float = 0.0
    confidence: float = 0.0
    assumptions: dict[str, float | int | str] = field(default_factory=dict)


@dataclass(slots=True)
class LBOReturnProfile:
    entry_enterprise_value: float
    exit_enterprise_value: float
    exit_equity_value: float
    irr: float
    moic: float
    debt_remaining: float
    holding_period_years: int


@dataclass(slots=True)
class ValuationSummary:
    company_name: str
    intrinsic_value_per_share: float | None
    fair_value_per_share: float | None
    current_price_per_share: float | None
    upside_downside_pct: float | None
    margin_of_safety_pct: float | None
    confidence: float
    recommendation: ValuationRecommendation
    executive_summary: str


@dataclass(slots=True)
class ValuationFinding:
    title: str
    description: str
    severity: str = "INFO"


@dataclass(slots=True)
class ScenarioOutcome:
    name: str
    exit_multiple: float
    irr: float
    moic: float
    exit_equity_value: float


@dataclass(slots=True)
class ScenarioAnalysis:
    target_irr: float
    outcomes: list[ScenarioOutcome] = field(default_factory=list)
    breakeven_exit_multiple: float | None = None


@dataclass(slots=True)
class ValuationReport:
    summary: ValuationSummary
    methods: list[ValuationMethod] = field(default_factory=list)
    lbo_returns: LBOReturnProfile | None = None
    scenario_analysis: ScenarioAnalysis | None = None
    findings: list[ValuationFinding] = field(default_factory=list)
    key_assumptions: dict[str, float | int | str] = field(default_factory=dict)
