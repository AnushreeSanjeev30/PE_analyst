import pytest

from lbo import LBOAssumptions, OperatingProjection
from lbo.sensitivity import SensitivityEngine


def _assumptions() -> LBOAssumptions:
    return LBOAssumptions(purchase_price=1_600.0, holding_period=5, exit_multiple=8.0)


def _projection() -> list[OperatingProjection]:
    return [
        OperatingProjection(
            year=year,
            revenue=1_000.0 + year * 60,
            ebitda=220.0 + year * 15,
            taxes=30.0 + year,
            capex=30.0 + year,
            change_in_nwc=10.0 + year,
        )
        for year in range(1, 6)
    ]


def test_grid_covers_every_combination_and_irr_increases_with_exit_multiple() -> None:
    engine = SensitivityEngine(_assumptions(), _projection())

    grid = engine.grid(exit_multiples=[6.0, 8.0, 10.0], ebitda_multipliers=[0.9, 1.0, 1.1])

    assert len(grid.cells) == 9
    low = next(c for c in grid.cells if c.exit_multiple == 6.0 and c.ebitda_multiplier == 1.0)
    high = next(c for c in grid.cells if c.exit_multiple == 10.0 and c.ebitda_multiplier == 1.0)
    assert high.irr > low.irr


def test_grid_rejects_empty_axes() -> None:
    engine = SensitivityEngine(_assumptions(), _projection())

    with pytest.raises(ValueError, match="non-empty"):
        engine.grid(exit_multiples=[], ebitda_multipliers=[1.0])


def test_breakeven_exit_multiple_hits_the_target_irr() -> None:
    engine = SensitivityEngine(_assumptions(), _projection())

    breakeven = engine.breakeven_exit_multiple(0.20)

    grid = engine.grid(exit_multiples=[breakeven], ebitda_multipliers=[1.0])
    assert grid.cells[0].irr == pytest.approx(0.20, abs=1e-3)


def test_breakeven_returns_low_bound_when_already_cleared() -> None:
    engine = SensitivityEngine(_assumptions(), _projection())

    breakeven = engine.breakeven_exit_multiple(0.01, low=8.0, high=25.0)

    assert breakeven == 8.0


def test_breakeven_raises_when_unreachable() -> None:
    engine = SensitivityEngine(_assumptions(), _projection())

    with pytest.raises(ValueError, match="not reachable"):
        engine.breakeven_exit_multiple(5.0, low=0.5, high=2.0)
