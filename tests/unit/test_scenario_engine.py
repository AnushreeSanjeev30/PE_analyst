import pytest

from lbo import LBOAssumptions, OperatingProjection
from lbo.scenario import DEFAULT_SCENARIOS, ScenarioAdjustment, ScenarioEngine


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


def test_default_scenarios_order_bear_to_bull_by_irr() -> None:
    results = ScenarioEngine(_assumptions(), _projection()).run()

    assert [outcome.name for outcome in results] == ["Bear", "Base", "Bull"]
    assert results[0].result.irr < results[1].result.irr < results[2].result.irr


def test_base_scenario_matches_an_unadjusted_lbo_run() -> None:
    from lbo.lbo_engine import LBOEngine

    assumptions = _assumptions()
    projection = _projection()
    baseline = LBOEngine(assumptions).run(projection)

    results = ScenarioEngine(assumptions, projection).run((ScenarioAdjustment("Base"),))

    assert results[0].result.irr == pytest.approx(baseline.irr)
    assert results[0].result.moic == pytest.approx(baseline.moic)


def test_custom_scenarios_are_respected() -> None:
    custom = (ScenarioAdjustment("Stress", ebitda_multiplier=0.5),)

    results = ScenarioEngine(_assumptions(), _projection()).run(custom)

    assert len(results) == 1
    assert results[0].name == "Stress"


def test_run_rejects_empty_scenario_list() -> None:
    with pytest.raises(ValueError, match="At least one scenario"):
        ScenarioEngine(_assumptions(), _projection()).run(())


def test_exit_multiple_delta_is_floored_above_zero() -> None:
    crushing = (ScenarioAdjustment("Collapse", exit_multiple_delta=-100.0),)

    results = ScenarioEngine(_assumptions(), _projection()).run(crushing)

    assert results[0].exit_multiple > 0


def test_default_scenarios_constant_is_immutable() -> None:
    assert isinstance(DEFAULT_SCENARIOS, tuple)
