"""Request contract for the deal-analysis API."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .assumptions import ValuationAssumptionInputs


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

    Supply the valuation either as ``valuation_assumptions`` (a dozen analyst decisions, expanded
    into the full inputs server-side) or as the raw nested ``valuation_inputs``. Exactly one is
    required.

    ``document_ids`` names every document the run should draw on; evidence is combined across
    them and financial figures are taken from the first document that reports each one, so list
    the most authoritative (audited accounts) first. ``document_id`` is the single-document
    form and is kept for existing callers.
    """

    company_name: str
    # Omit both to derive them from ``document_id``'s extracted statements.
    current_financials: FinancialStatementInput | None = None
    previous_financials: FinancialStatementInput | None = None
    # Patches for fields the document didn't yield: {"current": {...}, "previous": {...}}.
    financial_overrides: dict[str, dict[str, float]] | None = None
    valuation_inputs: dict[str, Any] | None = None
    valuation_assumptions: ValuationAssumptionInputs | None = None
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
    document_ids: list[str] = Field(
        default_factory=list,
        description="Every document to draw on, most authoritative first.",
    )
    industry_name: str = Field(
        default="",
        description="Required when industry_inputs is omitted and derived from documents.",
    )
    competitive_position: str | None = Field(
        default=None,
        description=(
            "Leader | Strong | Neutral | Weak. Used when industry_inputs is derived from "
            "documents; defaults to Neutral."
        ),
    )
    market_growth_pct: float | None = Field(
        default=None,
        description="Market growth as a decimal (0.12 = 12%), when derived from documents.",
    )
    deal_room_id: str | None = Field(
        default=None,
        description="File this analysis in a deal room, sharing it with that deal's team.",
    )

    @model_validator(mode="after")
    def _one_valuation_source(self) -> DealAnalysisRequest:
        if self.valuation_inputs is None and self.valuation_assumptions is None:
            raise ValueError("Provide valuation_assumptions or valuation_inputs")
        if self.valuation_inputs is not None and self.valuation_assumptions is not None:
            raise ValueError("Provide valuation_assumptions or valuation_inputs, not both")
        return self

    @property
    def all_document_ids(self) -> list[str]:
        """``document_ids`` plus the legacy ``document_id``, in order, without duplicates."""

        ids = list(self.document_ids)
        if self.document_id and self.document_id not in ids:
            ids.insert(0, self.document_id)
        return list(dict.fromkeys(ids))


class SuggestInputsRequest(BaseModel):
    """Documents to read proposed financials and valuation assumptions from."""

    document_ids: list[str] = Field(min_length=1)


class SensitivityRequest(BaseModel):
    """Ad-hoc two-way IRR sensitivity grid for one LBO case, independent of the full workflow."""

    lbo_assumptions: dict[str, Any]
    operating_projection: list[dict[str, Any]]
    exit_multiples: list[float] = Field(min_length=1)
    ebitda_multipliers: list[float] = Field(min_length=1)


class DealAnalysisSummary(BaseModel):
    """A saved analysis without its report -- what the history list shows."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    company_name: str
    # pending | running | completed | failed
    status: str
    recommendation: str | None = None
    document_id: str | None = None
    deal_room_id: str | None = None
    owner_id: str | None = None
    error: str | None = None
    created_at: datetime
    completed_at: datetime | None = None


class DealAnalysisRecord(DealAnalysisSummary):
    """A saved analysis with its full report (``None`` until the run finishes)."""

    report: dict[str, Any] | None = None


__all__ = [
    "DealAnalysisRecord",
    "DealAnalysisRequest",
    "DealAnalysisSummary",
    "FinancialStatementInput",
    "SensitivityRequest",
    "SuggestInputsRequest",
]
