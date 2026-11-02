"""Deterministic scenario, break-even and sensitivity analysis behind the Scenario Agent."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from lbo.assumptions import LBOAssumptions
from lbo.lbo_engine import LBOEngine
from lbo.scenario import ScenarioAdjustment, ScenarioEngine
from lbo.schemas import OperatingProjection
from lbo.sensitivity import SensitivityEngine, SensitivityGrid

from .scenario_models import ReturnResilience, ScenarioCase
from .valuation_tools import ValuationTools

DEFAULT_TARGET_IRR = 0.20

# (adjustment, probability) -- a conventional 25/50/25 bear/base/bull weighting.
DEFAULT_CASES: tuple[tuple[ScenarioAdjustment, float], ...] = (
    (
        ScenarioAdjustment(
            "Bear", revenue_multiplier=0.95, ebitda_multiplier=0.85, exit_multiple_delta=-1.0
        ),
        0.25,
    ),
    (ScenarioAdjustment("Base"), 0.50),
    (
        ScenarioAdjustment(
            "Bull", revenue_multiplier=1.05, ebitda_multiplier=1.10, exit_multiple_delta=1.0
        ),
        0.25,
    ),
)

_EXIT_MULTIPLE_STEPS = (-2.0, -1.0, 0.0, 1.0, 2.0)
_EBITDA_MULTIPLIERS = (0.80, 0.90, 1.00, 1.10, 1.20)


class ScenarioTools:
    @staticmethod
    def parse_lbo(lbo_input: dict[str, Any]) -> tuple[LBOAssumptions, list[OperatingProjection]]:
        if "assumptions" not in lbo_input or "operating_projection" not in lbo_input:
            raise ValueError("Scenario analysis requires lbo assumptions and operating_projection")
        assumptions = ValuationTools._coerce_lbo_assumptions(lbo_input["assumptions"])
        projection = [
            ValuationTools._coerce_projection(item) for item in lbo_input["operating_projection"]
        ]
        if len(projection) != assumptions.holding_period:
            raise ValueError("LBO operating_projection length must equal holding_period")
        return assumptions, projection

    @staticmethod
    def parse_cases(raw: list[dict[str, Any]] | None) -> list[tuple[ScenarioAdjustment, float]]:
        if not raw:
            return list(DEFAULT_CASES)
        cases = [
            (
                ScenarioAdjustment(
                    str(item["name"]),
                    float(item.get("revenue_multiplier", 1.0)),
                    float(item.get("ebitda_multiplier", 1.0)),
                    float(item.get("exit_multiple_delta", 0.0)),
                ),
                float(item.get("probability", 0.0)),
            )
            for item in raw
        ]
        total = sum(probability for _, probability in cases)
        if total <= 0:
            equal = 1.0 / len(cases)
            return [(adjustment, equal) for adjustment, _ in cases]
        return [(adjustment, probability / total) for adjustment, probability in cases]

    @staticmethod
    def run_cases(
        assumptions: LBOAssumptions,
        projection: list[OperatingProjection],
        cases: list[tuple[ScenarioAdjustment, float]],
        target_irr: float,
    ) -> list[ScenarioCase]:
        results = ScenarioEngine(assumptions, projection).run(
            tuple(adjustment for adjustment, _ in cases)
        )
        return [
            ScenarioCase(
                name=result.name,
                probability=probability,
                revenue_multiplier=result.adjustment.revenue_multiplier,
                ebitda_multiplier=result.adjustment.ebitda_multiplier,
                exit_multiple=result.exit_multiple,
                irr=result.result.irr,
                moic=result.result.moic,
                exit_equity_value=result.result.exit_equity,
                meets_target=result.result.irr >= target_irr,
            )
            for result, (_, probability) in zip(results, cases, strict=True)
        ]

    @staticmethod
    def breakeven(
        assumptions: LBOAssumptions, projection: list[OperatingProjection], target_irr: float
    ) -> float | None:
        try:
            return SensitivityEngine(assumptions, projection).breakeven_exit_multiple(target_irr)
        except ValueError:
            return None

    @staticmethod
    def capital_preservation_multiple(
        assumptions: LBOAssumptions,
        projection: list[OperatingProjection],
        *,
        low: float = 0.5,
        high: float = 25.0,
        iterations: int = 50,
    ) -> float | None:
        """Lowest exit multiple at which equity gets its money back (MOIC >= 1.0x)."""

        def moic(multiple: float) -> float:
            scenario = replace(assumptions, exit_multiple=multiple)
            return LBOEngine(scenario).run(projection).moic

        if moic(low) >= 1.0:
            return low
        if moic(high) < 1.0:
            return None
        for _ in range(iterations):
            mid = (low + high) / 2
            if moic(mid) >= 1.0:
                high = mid
            else:
                low = mid
        return high

    @staticmethod
    def sensitivity(
        assumptions: LBOAssumptions,
        projection: list[OperatingProjection],
        exit_multiples: list[float] | None = None,
        ebitda_multipliers: list[float] | None = None,
    ) -> SensitivityGrid:
        multiples = exit_multiples or [
            round(assumptions.exit_multiple + step, 2)
            for step in _EXIT_MULTIPLE_STEPS
            if assumptions.exit_multiple + step > 0
        ]
        return SensitivityEngine(assumptions, projection).grid(
            multiples, ebitda_multipliers or list(_EBITDA_MULTIPLIERS)
        )

    @staticmethod
    def resilience(cases: list[ScenarioCase], weighted_irr: float, target_irr: float) -> (
        ReturnResilience
    ):
        worst = min(cases, key=lambda case: case.irr)
        if worst.moic < 1.0 or weighted_irr < target_irr * 0.75:
            return ReturnResilience.FRAGILE
        if worst.irr >= target_irr * 0.75 and weighted_irr >= target_irr:
            return ReturnResilience.RESILIENT
        return ReturnResilience.BALANCED


__all__ = ["DEFAULT_CASES", "DEFAULT_TARGET_IRR", "ScenarioTools"]
