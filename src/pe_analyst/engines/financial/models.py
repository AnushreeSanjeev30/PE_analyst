"""
Financial domain models used by the financial analysis engine.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class FinancialStatement:
    """
    Simplified financial statement.

    All monetary values should use the same currency.
    """

    revenue: float

    cost_of_goods_sold: float

    ebitda: float

    ebit: float

    net_income: float

    operating_cash_flow: float

    capital_expenditure: float

    total_assets: float

    shareholders_equity: float

    total_debt: float

    interest_expense: float

    current_assets: float

    inventory: float

    current_liabilities: float


@dataclass(slots=True, frozen=True)
class GrowthMetrics:
    revenue_growth: float

    ebitda_growth: float

    earnings_growth: float