"""Deterministic scenario analysis: stress-tests an LBO case across named operating scenarios.

Each scenario perturbs the base operating projection (revenue/EBITDA) and exit multiple, then
reruns the existing :class:`LBOEngine` end to end -- no new return-calculation logic, just
composition of what already exists.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .assumptions import LBOAssumptions
from .lbo_engine import LBOEngine
from .schemas import LBOResult, OperatingProjection


@dataclass(slots=True, frozen=True)
class ScenarioAdjustment:
    """Deltas applied to the base case to produce one named scenario."""

    name: str
    revenue_multiplier: float = 1.0
    ebitda_multiplier: float = 1.0
    exit_multiple_delta: float = 0.0


@dataclass(slots=True)
class ScenarioResult:
    name: str
    adjustment: ScenarioAdjustment
    exit_multiple: float
    result: LBOResult


DEFAULT_SCENARIOS: tuple[ScenarioAdjustment, ...] = (
    ScenarioAdjustment(
        "Bear", revenue_multiplier=0.95, ebitda_multiplier=0.85, exit_multiple_delta=-1.0
    ),
    ScenarioAdjustment("Base"),
    ScenarioAdjustment(
        "Bull", revenue_multiplier=1.05, ebitda_multiplier=1.10, exit_multiple_delta=1.0
    ),
)

_MIN_EXIT_MULTIPLE = 0.1


class ScenarioEngine:
    """Runs the LBO engine across a set of named operating scenarios."""

    def __init__(
        self, assumptions: LBOAssumptions, operating_projection: list[OperatingProjection]
    ) -> None:
        self.assumptions = assumptions
        self.operating_projection = operating_projection

    def run(
        self, scenarios: tuple[ScenarioAdjustment, ...] = DEFAULT_SCENARIOS
    ) -> list[ScenarioResult]:
        if not scenarios:
            raise ValueError("At least one scenario is required")
        return [self._run_one(scenario) for scenario in scenarios]

    def _run_one(self, scenario: ScenarioAdjustment) -> ScenarioResult:
        exit_multiple = max(
            _MIN_EXIT_MULTIPLE, self.assumptions.exit_multiple + scenario.exit_multiple_delta
        )
        scenario_assumptions = replace(self.assumptions, exit_multiple=exit_multiple)
        scenario_assumptions.validate()
        scenario_projection = [
            replace(
                item,
                revenue=item.revenue * scenario.revenue_multiplier,
                ebitda=item.ebitda * scenario.ebitda_multiplier,
            )
            for item in self.operating_projection
        ]
        result = LBOEngine(scenario_assumptions).run(scenario_projection)
        return ScenarioResult(scenario.name, scenario, exit_multiple, result)


__all__ = ["DEFAULT_SCENARIOS", "ScenarioAdjustment", "ScenarioEngine", "ScenarioResult"]
