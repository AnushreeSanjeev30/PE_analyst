"""
Financial ratio calculations.

All ratio functions are deterministic and side-effect free.

Returns
-------
float
    Ratio represented as a decimal.
    Example:
        0.25 == 25%
"""

from __future__ import annotations

from math import isfinite


class FinancialCalculationError(ValueError):
    """Raised when financial inputs are invalid."""


def _validate_number(value: float, name: str) -> None:
    """Validate that a numeric value is finite."""
    if not isfinite(value):
        raise FinancialCalculationError(f"{name} must be finite.")


def _safe_divide(
    numerator: float,
    denominator: float,
    *,
    allow_zero: bool = False,
) -> float:
    """
    Divide two numbers safely.

    Raises
    ------
    ZeroDivisionError
        If denominator is zero and allow_zero=False.
    """
    if denominator == 0:
        if allow_zero:
            return 0.0
        raise ZeroDivisionError("Division by zero.")

    return numerator / denominator


def current_ratio(
    current_assets: float,
    current_liabilities: float,
) -> float:
    """
    Current Ratio.

    Formula
    -------
    Current Assets / Current Liabilities
    """
    _validate_number(current_assets, "current_assets")
    _validate_number(current_liabilities, "current_liabilities")

    return _safe_divide(
        current_assets,
        current_liabilities,
    )


def quick_ratio(
    current_assets: float,
    inventory: float,
    current_liabilities: float,
) -> float:
    """
    Quick Ratio.

    Formula
    -------
    (Current Assets - Inventory) / Current Liabilities
    """
    _validate_number(current_assets, "current_assets")
    _validate_number(inventory, "inventory")
    _validate_number(current_liabilities, "current_liabilities")

    return _safe_divide(
        current_assets - inventory,
        current_liabilities,
    )


def gross_margin(
    revenue: float,
    cost_of_goods_sold: float,
) -> float:
    """
    Gross Margin.

    Formula
    -------
    (Revenue - COGS) / Revenue
    """
    _validate_number(revenue, "revenue")
    _validate_number(cost_of_goods_sold, "cost_of_goods_sold")

    gross_profit = revenue - cost_of_goods_sold

    return _safe_divide(
        gross_profit,
        revenue,
    )


def ebitda_margin(
    revenue: float,
    ebitda: float,
) -> float:
    """
    EBITDA Margin.

    Formula
    -------
    EBITDA / Revenue
    """
    _validate_number(revenue, "revenue")
    _validate_number(ebitda, "ebitda")

    return _safe_divide(
        ebitda,
        revenue,
    )


def net_margin(
    revenue: float,
    net_income: float,
) -> float:
    """
    Net Profit Margin.

    Formula
    -------
    Net Income / Revenue
    """
    _validate_number(revenue, "revenue")
    _validate_number(net_income, "net_income")

    return _safe_divide(
        net_income,
        revenue,
    )


def return_on_assets(
    net_income: float,
    total_assets: float,
) -> float:
    """
    Return on Assets.

    Formula
    -------
    Net Income / Total Assets
    """
    _validate_number(net_income, "net_income")
    _validate_number(total_assets, "total_assets")

    return _safe_divide(
        net_income,
        total_assets,
    )


def return_on_equity(
    net_income: float,
    shareholders_equity: float,
) -> float:
    """
    Return on Equity.

    Formula
    -------
    Net Income / Shareholders' Equity
    """
    _validate_number(net_income, "net_income")
    _validate_number(shareholders_equity, "shareholders_equity")

    return _safe_divide(
        net_income,
        shareholders_equity,
    )


def debt_to_ebitda(
    total_debt: float,
    ebitda: float,
) -> float:
    """
    Debt / EBITDA.
    """
    _validate_number(total_debt, "total_debt")
    _validate_number(ebitda, "ebitda")

    return _safe_divide(
        total_debt,
        ebitda,
    )


def interest_coverage(
    ebit: float,
    interest_expense: float,
) -> float:
    """
    Interest Coverage.

    Formula
    -------
    EBIT / Interest Expense
    """
    _validate_number(ebit, "ebit")
    _validate_number(interest_expense, "interest_expense")

    return _safe_divide(
        ebit,
        interest_expense,
    )


def asset_turnover(
    revenue: float,
    average_assets: float,
) -> float:
    """
    Asset Turnover.

    Formula
    -------
    Revenue / Average Assets
    """
    _validate_number(revenue, "revenue")
    _validate_number(average_assets, "average_assets")

    return _safe_divide(
        revenue,
        average_assets,
    )