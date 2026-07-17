"""Unit tests for financial ratio calculations."""

from __future__ import annotations

import math

import pytest

from pe_analyst.engines.financial import (
    asset_turnover,
    current_ratio,
    debt_to_ebitda,
    ebitda_margin,
    gross_margin,
    interest_coverage,
    net_margin,
    quick_ratio,
    return_on_assets,
    return_on_equity,
)
from pe_analyst.engines.financial.ratios import FinancialCalculationError

# ---------------------------------------------------------------------
# Current Ratio
# ---------------------------------------------------------------------


def test_current_ratio() -> None:
    assert current_ratio(500, 250) == pytest.approx(2.0)


def test_current_ratio_fraction() -> None:
    assert current_ratio(900, 600) == pytest.approx(1.5)


def test_current_ratio_zero_division() -> None:
    with pytest.raises(ZeroDivisionError):
        current_ratio(100, 0)


# ---------------------------------------------------------------------
# Quick Ratio
# ---------------------------------------------------------------------


def test_quick_ratio() -> None:
    assert quick_ratio(1000, 200, 400) == pytest.approx(2.0)


def test_quick_ratio_zero_inventory() -> None:
    assert quick_ratio(600, 0, 300) == pytest.approx(2.0)


def test_quick_ratio_zero_division() -> None:
    with pytest.raises(ZeroDivisionError):
        quick_ratio(100, 20, 0)


# ---------------------------------------------------------------------
# Gross Margin
# ---------------------------------------------------------------------


def test_gross_margin() -> None:
    assert gross_margin(1000, 600) == pytest.approx(0.4)


def test_gross_margin_full_cost() -> None:
    assert gross_margin(1000, 1000) == pytest.approx(0.0)


def test_gross_margin_zero_revenue() -> None:
    with pytest.raises(ZeroDivisionError):
        gross_margin(0, 10)


# ---------------------------------------------------------------------
# EBITDA Margin
# ---------------------------------------------------------------------


def test_ebitda_margin() -> None:
    assert ebitda_margin(1000, 250) == pytest.approx(0.25)


def test_ebitda_margin_negative() -> None:
    assert ebitda_margin(1000, -50) == pytest.approx(-0.05)


def test_ebitda_margin_zero_revenue() -> None:
    with pytest.raises(ZeroDivisionError):
        ebitda_margin(0, 10)


# ---------------------------------------------------------------------
# Net Margin
# ---------------------------------------------------------------------


def test_net_margin() -> None:
    assert net_margin(1000, 150) == pytest.approx(0.15)


def test_net_margin_loss() -> None:
    assert net_margin(1000, -100) == pytest.approx(-0.10)


# ---------------------------------------------------------------------
# Return on Assets
# ---------------------------------------------------------------------


def test_return_on_assets() -> None:
    assert return_on_assets(100, 1000) == pytest.approx(0.10)


def test_return_on_assets_zero_assets() -> None:
    with pytest.raises(ZeroDivisionError):
        return_on_assets(100, 0)


# ---------------------------------------------------------------------
# Return on Equity
# ---------------------------------------------------------------------


def test_return_on_equity() -> None:
    assert return_on_equity(120, 600) == pytest.approx(0.20)


def test_return_on_equity_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        return_on_equity(120, 0)


# ---------------------------------------------------------------------
# Debt / EBITDA
# ---------------------------------------------------------------------


def test_debt_to_ebitda() -> None:
    assert debt_to_ebitda(500, 100) == pytest.approx(5.0)


def test_debt_to_ebitda_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        debt_to_ebitda(500, 0)


# ---------------------------------------------------------------------
# Interest Coverage
# ---------------------------------------------------------------------


def test_interest_coverage() -> None:
    assert interest_coverage(300, 60) == pytest.approx(5.0)


def test_interest_coverage_zero() -> None:
    with pytest.raises(ZeroDivisionError):
        interest_coverage(100, 0)


# ---------------------------------------------------------------------
# Asset Turnover
# ---------------------------------------------------------------------


def test_asset_turnover() -> None:
    assert asset_turnover(1200, 600) == pytest.approx(2.0)


def test_asset_turnover_zero_assets() -> None:
    with pytest.raises(ZeroDivisionError):
        asset_turnover(1000, 0)


# ---------------------------------------------------------------------
# Invalid Numeric Inputs
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_invalid_current_assets(value: float) -> None:
    with pytest.raises(FinancialCalculationError):
        current_ratio(value, 100)


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_invalid_revenue(value: float) -> None:
    with pytest.raises(FinancialCalculationError):
        gross_margin(value, 10)


@pytest.mark.parametrize(
    "value",
    [
        math.inf,
        -math.inf,
        math.nan,
    ],
)
def test_invalid_ebitda(value: float) -> None:
    with pytest.raises(FinancialCalculationError):
        ebitda_margin(1000, value)