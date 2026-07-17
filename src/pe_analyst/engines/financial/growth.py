"""
Growth metric calculations.
"""

from __future__ import annotations

from math import isfinite
from typing import cast


class GrowthCalculationError(ValueError):
    """Raised for invalid growth calculations."""


def _validate(value: float, name: str) -> None:
    if not isfinite(value):
        raise GrowthCalculationError(f"{name} must be finite.")


def growth_rate(
    previous: float,
    current: float,
) -> float:
    """
    Calculate period-over-period growth.

    Returns
    -------
    decimal
        Example:
        0.15 = 15%
    """
    _validate(previous, "previous")
    _validate(current, "current")

    if previous == 0:
        raise ZeroDivisionError(
            "Previous period cannot be zero."
        )

    return (current - previous) / previous


def cagr(
    beginning: float,
    ending: float,
    periods: int,
) -> float:
    """
    Compound Annual Growth Rate.
    """
    _validate(beginning, "beginning")
    _validate(ending, "ending")

    if beginning <= 0:
        raise ValueError(
            "Beginning value must be positive."
        )

    if periods <= 0:
        raise ValueError(
            "Periods must be positive."
        )

    return cast(float, (ending / beginning) ** (1 / periods) - 1)


def average_growth(
    growth_rates: list[float],
) -> float:
    """
    Arithmetic mean of growth rates.
    """
    if not growth_rates:
        raise ValueError(
            "Growth rate list cannot be empty."
        )

    for value in growth_rates:
        _validate(value, "growth rate")

    total_growth: float = 0.0
    for value in growth_rates:
        total_growth += value

    return total_growth / len(growth_rates)


def project_value(
    current_value: float,
    annual_growth_rate: float,
    years: int,
) -> float:
    """
    Compound growth projection.
    """
    _validate(current_value, "current_value")
    _validate(annual_growth_rate, "annual_growth_rate")

    if years < 0:
        raise ValueError(
            "Years cannot be negative."
        )

    return current_value * (
        (1 + annual_growth_rate) ** years
    )