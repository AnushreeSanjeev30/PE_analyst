"""Request contract for the deal-analysis API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FinancialStatementInput(BaseModel):
    """Mirrors ``pe_analyst.engines.financial.models.FinancialStatement``."""

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


class DealAnalysisRequest(BaseModel):
    """Inputs for one end-to-end underwriting run.

    ``industry_inputs`` and ``due_diligence_inputs`` may be supplied directly, or left out and
    derived automatically from a previously uploaded document's extracted evidence by passing
    ``document_id`` (see ``document_intelligence.agent_inputs``). Explicit values always win.

    ``valuation_inputs.comparables`` may carry ``peer_tickers`` instead of ``peers``; they are
    looked up through the configured market-data provider.
    """

    company_name: str
    # Omit both to derive them from ``document_id``'s extracted statements.
    current_financials: FinancialStatementInput | None = None
    previous_financials: FinancialStatementInput | None = None
    # Patches for fields the document didn't yield: {"current": {...}, "previous": {...}}.
    financial_overrides: dict[str, dict[str, float]] | None = None
    valuation_inputs: dict[str, Any]
    risk_inputs: dict[str, Any] | None = None
    scenario_inputs: dict[str, Any] | None = Field(
        default=None,
        description=(
            "Optional Scenario Agent overrides: target_irr, scenarios (name, probability, "
            "revenue_multiplier, ebitda_multiplier, exit_multiple_delta), exit_multiples, "
            "ebitda_multipliers."
        ),
    )
    industry_inputs: dict[str, Any] | None = None
    due_diligence_inputs: list[dict[str, Any]] | None = None
    document_id: str | None = Field(
        default=None,
        description=(
            "A previously processed document's id. When industry_inputs or "
            "due_diligence_inputs are omitted, they are derived from this document's "
            "extracted industry evidence and risk factors/notes."
        ),
    )
    industry_name: str = Field(
        default="",
        description="Required when industry_inputs is omitted and derived from document_id.",
    )


class SensitivityRequest(BaseModel):
    """Ad-hoc two-way IRR sensitivity grid for one LBO case, independent of the full workflow."""

    lbo_assumptions: dict[str, Any]
    operating_projection: list[dict[str, Any]]
    exit_multiples: list[float] = Field(min_length=1)
    ebitda_multipliers: list[float] = Field(min_length=1)


__all__ = ["DealAnalysisRequest", "FinancialStatementInput", "SensitivityRequest"]
