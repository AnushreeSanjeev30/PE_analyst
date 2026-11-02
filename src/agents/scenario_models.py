"""Typed output contracts for the Scenario Analysis Agent."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from lbo.sensitivity import SensitivityGrid


class ReturnResilience(StrEnum):
    RESILIENT = "Resilient"
    BALANCED = "Balanced"
    FRAGILE = "Fragile"


@dataclass(slots=True)
class ScenarioCase:
    name: str
    probability: float
    revenue_multiplier: float
    ebitda_multiplier: float
    exit_multiple: float
    irr: float
    moic: float
    exit_equity_value: float
    meets_target: bool


@dataclass(slots=True)
class ScenarioSummary:
    company_name: str
    resilience: ReturnResilience
    target_irr: float
    probability_weighted_irr: float
    probability_weighted_moic: float
    confidence: float
    executive_summary: str


@dataclass(slots=True)
class ScenarioReport:
    summary: ScenarioSummary
    cases: list[ScenarioCase] = field(default_factory=list)
    breakeven_exit_multiple: float | None = None
    capital_preservation_exit_multiple: float | None = None
    probability_of_meeting_target: float = 0.0
    downside_capital_loss: bool = False
    sensitivity: SensitivityGrid | None = None
    findings: list[str] = field(default_factory=list)
