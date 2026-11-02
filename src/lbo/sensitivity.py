"""Deterministic two-way sensitivity and break-even analysis, built on the LBO engine.

Holds operating results at a caller-supplied EBITDA multiplier and the exit multiple at a
caller-supplied level, reruns :class:`LBOEngine`, and reports IRR/MOIC at each combination --
and, separately, the minimum exit multiple needed to clear a target IRR, found by bisection
(IRR is monotonically increasing in exit multiple with everything else held fixed).
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .assumptions import LBOAssumptions
from .lbo_engine import LBOEngine
from .schemas import OperatingProjection


@dataclass(slots=True, frozen=True)
class SensitivityCell:
    exit_multiple: float
    ebitda_multiplier: float
    irr: float
    moic: float


@dataclass(slots=True)
class SensitivityGrid:
    exit_multiples: list[float]
    ebitda_multipliers: list[float]
    cells: list[SensitivityCell]


class SensitivityEngine:
    def __init__(
        self, assumptions: LBOAssumptions, operating_projection: list[OperatingProjection]
    ) -> None:
        self.assumptions = assumptions
        self.operating_projection = operating_projection

    def _run(self, exit_multiple: float, ebitda_multiplier: float) -> tuple[float, float]:
        scenario_assumptions = replace(self.assumptions, exit_multiple=exit_multiple)
        scenario_assumptions.validate()
        projection = [
            replace(item, ebitda=item.ebitda * ebitda_multiplier)
            for item in self.operating_projection
        ]
        result = LBOEngine(scenario_assumptions).run(projection)
        return result.irr, result.moic

    def grid(
        self, exit_multiples: list[float], ebitda_multipliers: list[float]
    ) -> SensitivityGrid:
        if not exit_multiples or not ebitda_multipliers:
            raise ValueError("exit_multiples and ebitda_multipliers must be non-empty")
        cells = [
            SensitivityCell(
                exit_multiple, ebitda_multiplier, *self._run(exit_multiple, ebitda_multiplier)
            )
            for exit_multiple in exit_multiples
            for ebitda_multiplier in ebitda_multipliers
        ]
        return SensitivityGrid(list(exit_multiples), list(ebitda_multipliers), cells)

    def breakeven_exit_multiple(
        self,
        target_irr: float,
        *,
        low: float = 0.5,
        high: float = 25.0,
        tolerance: float = 1e-4,
        max_iterations: int = 60,
    ) -> float:
        """Bisect for the minimum exit multiple (base-case operating results) hitting target_irr."""

        irr_low, _ = self._run(low, 1.0)
        if irr_low >= target_irr:
            return low
        irr_high, _ = self._run(high, 1.0)
        if irr_high < target_irr:
            raise ValueError(
                f"Target IRR {target_irr:.1%} is not reachable within exit multiple bounds "
                f"[{low}, {high}]"
            )
        for _ in range(max_iterations):
            mid = (low + high) / 2
            irr_mid, _ = self._run(mid, 1.0)
            if abs(irr_mid - target_irr) <= tolerance:
                return mid
            if irr_mid < target_irr:
                low = mid
            else:
                high = mid
        return (low + high) / 2


__all__ = ["SensitivityCell", "SensitivityEngine", "SensitivityGrid"]
