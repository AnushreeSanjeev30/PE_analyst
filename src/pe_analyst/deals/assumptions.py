"""Turns a short list of analyst assumptions into the full valuation inputs, and proposes
those assumptions from the uploaded documents.

The valuation engines take a nested structure: DCF assumptions, a comparables target, an LBO
case and a year-by-year operating projection. Typing that as JSON is slow and easy to get
wrong, and most of it is arithmetic on a dozen real decisions (growth, margin, the price paid,
the exit multiple). ``ValuationAssumptionInputs`` is that dozen; ``build_valuation_inputs``
does the arithmetic.

``suggest_inputs`` goes one step further and proposes a value for each assumption from the
documents, so the analyst confirms and corrects rather than starts from a blank form. It uses
fixed rules, never an LLM, and every proposal says where it came from:

* ``Document``    -- a figure or phrase read from a cited page.
* ``Calculated``  -- arithmetic on figures read from the documents.
* ``Default``     -- a house default. Nothing in the documents supports it; the analyst must
                     set it.
* ``Needs input`` -- not found and no sensible default exists.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import Any

from pydantic import BaseModel, Field

from pe_analyst.document_intelligence.agent_inputs import (
    build_financial_evidence,
    map_financials_across,
)
from pe_analyst.document_intelligence.financial_mapping import (
    STATEMENT_FIELDS,
    normalize_label,
)
from pe_analyst.document_intelligence.schemas import (
    DocumentIntelligenceReport,
    display_name,
)
from pe_analyst.engines.financial.models import FinancialStatement

BASIS_DOCUMENT = "Document"
BASIS_CALCULATED = "Calculated"
BASIS_DEFAULT = "Default"
BASIS_NEEDS_INPUT = "Needs input"

DEFAULT_TAX_RATE = 0.25
DEFAULT_NWC_PCT = 0.02
DEFAULT_ENTRY_MULTIPLE = 8.0
DEFAULT_HOLDING_PERIOD = 5


class PeerInput(BaseModel):
    """One comparable company. Mirrors ``pe_analyst.valuation.PeerCompany``."""

    name: str
    enterprise_value: float
    market_cap: float
    revenue: float
    ebitda: float
    net_income: float
    book_value: float = 0.0


class ValuationAssumptionInputs(BaseModel):
    """The decisions behind a valuation. Rates and margins are decimals (0.08 = 8%); money is
    in the same units as the financial statements."""

    revenue_growth: float = Field(description="Annual revenue growth over the projection.")
    ebit_margin: float = Field(description="Operating profit as a share of revenue.")
    ebitda_margin: float = Field(gt=0, description="EBITDA as a share of revenue.")
    tax_rate: float = Field(default=DEFAULT_TAX_RATE, ge=0, le=1)
    capex_pct_revenue: float = Field(default=0.04, ge=0)
    nwc_pct_revenue: float = Field(
        default=DEFAULT_NWC_PCT,
        ge=0,
        description="Working capital tied up per unit of revenue growth.",
    )
    cash: float = Field(default=0.0, ge=0)
    debt: float = Field(default=0.0, ge=0)
    shares_outstanding: float = Field(gt=0)
    current_price_per_share: float | None = Field(default=None, gt=0)
    entry_multiple: float = Field(gt=0, description="Purchase price as a multiple of EBITDA.")
    exit_multiple: float = Field(gt=0, description="Sale price as a multiple of exit EBITDA.")
    holding_period: int = Field(default=DEFAULT_HOLDING_PERIOD, ge=1, le=15)
    peers: list[PeerInput] = Field(default_factory=list)
    peer_tickers: list[str] = Field(default_factory=list)


def build_valuation_inputs(
    assumptions: ValuationAssumptionInputs, current: FinancialStatement
) -> dict[str, Any]:
    """Expand analyst assumptions into the nested inputs the valuation engines consume.

    Revenue and EBITDA start from the current-period statement. The LBO is priced at
    ``entry_multiple`` x current EBITDA, and its operating projection grows revenue at
    ``revenue_growth`` holding the margins constant.
    """

    if current.revenue <= 0:
        raise ValueError("Revenue must be positive to build a valuation.")
    if current.ebitda <= 0:
        raise ValueError(
            "EBITDA must be positive to price a leveraged buyout on an EBITDA multiple. "
            "Enter the valuation inputs directly for a loss-making company."
        )
    if len(assumptions.peers) < 2 and not assumptions.peer_tickers:
        raise ValueError("Add at least two comparable companies, or peer tickers to look up.")

    projection = []
    previous_revenue = current.revenue
    for year in range(1, assumptions.holding_period + 1):
        revenue = current.revenue * (1 + assumptions.revenue_growth) ** year
        projection.append(
            {
                "year": year,
                "revenue": revenue,
                "ebitda": revenue * assumptions.ebitda_margin,
                "taxes": max(0.0, revenue * assumptions.ebit_margin) * assumptions.tax_rate,
                "capex": revenue * assumptions.capex_pct_revenue,
                "change_in_nwc": (revenue - previous_revenue) * assumptions.nwc_pct_revenue,
            }
        )
        previous_revenue = revenue

    comparables: dict[str, Any] = {
        "target": {
            "revenue": current.revenue,
            "ebitda": current.ebitda,
            "cash": assumptions.cash,
            "debt": assumptions.debt,
            "shares_outstanding": assumptions.shares_outstanding,
        }
    }
    if assumptions.peers:
        comparables["peers"] = [peer.model_dump() for peer in assumptions.peers]
    else:
        comparables["peer_tickers"] = assumptions.peer_tickers

    inputs: dict[str, Any] = {
        "dcf": {
            "revenue": current.revenue,
            "assumptions": {
                "projection_years": assumptions.holding_period,
                "revenue_growth": assumptions.revenue_growth,
                "ebit_margin": assumptions.ebit_margin,
                "tax_rate": assumptions.tax_rate,
                "capex_pct": assumptions.capex_pct_revenue,
                "nwc_pct": assumptions.nwc_pct_revenue,
                "cash": assumptions.cash,
                "debt": assumptions.debt,
                "shares_outstanding": assumptions.shares_outstanding,
            },
        },
        "comparables": comparables,
        "lbo": {
            "assumptions": {
                "purchase_price": assumptions.entry_multiple * current.ebitda,
                "holding_period": assumptions.holding_period,
                "exit_multiple": assumptions.exit_multiple,
                "tax_rate": assumptions.tax_rate,
            },
            "operating_projection": projection,
        },
    }
    if assumptions.current_price_per_share is not None:
        inputs["current_price_per_share"] = assumptions.current_price_per_share
    return inputs


# ---------------------------------------------------------------------------
# Suggestions
# ---------------------------------------------------------------------------


class SuggestionCitation(BaseModel):
    document_id: str
    source: str
    page_number: int
    excerpt: str


class Suggestion(BaseModel):
    """A proposed value for one input, with where it came from."""

    field: str
    label: str
    # None when nothing could be proposed (basis "Needs input").
    value: float | str | None
    basis: str
    note: str
    citation: SuggestionCitation | None = None


class SuggestedInputs(BaseModel):
    """Everything the New Analysis form can be pre-filled with from a set of documents."""

    # Statement fields read from the documents, in the documents' own units.
    current_financials: dict[str, float]
    previous_financials: dict[str, float]
    # Statement fields that could not be read for both periods; the analyst must type them.
    missing_financials: list[str]
    financial_sources: list[SuggestionCitation]
    warnings: list[str]
    assumptions: list[Suggestion]
    competitive_position: Suggestion
    market_growth_pct: Suggestion


_SENTENCE = re.compile(r"(?<=[.!?;])\s+")

# Phrases that signal competitive standing. Checked in this order within each sentence, so the
# strongest claim wins; a sentence that negates itself ("no longer the market leader") is
# skipped.
_POSITION_SIGNALS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "Leader",
        (
            "market leader", "leading position", "leading provider", "market-leading",
            "largest provider", "number one", "no. 1", "#1",
        ),
    ),
    (
        "Strong",
        (
            "strong competitive position", "strong market position", "strong position",
            "gaining share", "gained share", "market share gains", "high switching costs",
            "differentiated",
        ),
    ),
    (
        "Weak",
        (
            "losing share", "lost share", "lost market share", "take share from",
            "took share from", "taking share from", "competition is intense",
            "intense competition", "pricing pressure", "price pressure", "commoditi",
        ),
    ),
)
_NEGATIONS = ("no longer", "not a ", "not the ", "lack ", "lacks ", "without ")

_GROWTH = re.compile(
    r"(?:market|industry|demand|sector)[^.;]{0,90}?"
    r"\b(grew|growth of|growing at|grow at|increased|rose|expanded|"
    r"fell|declined|decreased|contracted|shrank)\b"
    r"[^.;\d]{0,25}?(\d+(?:\.\d+)?)\s*%",
    re.IGNORECASE,
)
_DECLINE_WORDS = {"fell", "declined", "decreased", "contracted", "shrank"}

_CASH_LABELS = ("cash and cash equivalents", "cash and equivalents", "cash")
_SHARE_LABELS = (
    "shares outstanding", "common shares outstanding", "weighted average shares outstanding",
    "weighted average shares", "diluted weighted average shares",
)


def _passages(
    reports: Sequence[DocumentIntelligenceReport],
) -> list[tuple[DocumentIntelligenceReport, int, str]]:
    """Every extracted sentence that could speak to market or competitive position."""

    passages: list[tuple[DocumentIntelligenceReport, int, str]] = []
    seen: set[tuple[str, int, str]] = set()
    for report in reports:
        texts = [(item.page_number, item.excerpt) for item in report.industry_evidence]
        texts += [(item.page_number, item.excerpt) for item in report.management_discussion]
        texts += [(item.source.page_number, item.text) for item in report.risk_factors]
        for page_number, text in texts:
            for sentence in _SENTENCE.split(" ".join(text.split())):
                key = (report.document_id, page_number, sentence)
                if sentence and key not in seen:
                    seen.add(key)
                    passages.append((report, page_number, sentence))
    return passages


def _cite(report: DocumentIntelligenceReport, page_number: int, excerpt: str) -> (
    SuggestionCitation
):
    return SuggestionCitation(
        document_id=report.document_id,
        source=display_name(report.file_name),
        page_number=page_number,
        excerpt=excerpt[:400],
    )


def suggest_competitive_position(reports: Sequence[DocumentIntelligenceReport]) -> Suggestion:
    """Propose Leader / Strong / Neutral / Weak from how the documents describe the company.

    This reads the company's own wording, which is marketing as much as fact. It is a starting
    point to confirm, and the note says so.
    """

    found: dict[str, tuple[DocumentIntelligenceReport, int, str]] = {}
    for report, page_number, sentence in _passages(reports):
        lowered = sentence.lower()
        if any(negation in lowered for negation in _NEGATIONS):
            continue
        for position, phrases in _POSITION_SIGNALS:
            if position not in found and any(phrase in lowered for phrase in phrases):
                found[position] = (report, page_number, sentence)
                break

    positive = "Leader" if "Leader" in found else "Strong" if "Strong" in found else None
    label = "Competitive position"
    if positive and "Weak" in found:
        report, page_number, sentence = found[positive]
        weak_report, weak_page, weak_sentence = found["Weak"]
        return Suggestion(
            field="competitive_position",
            label=label,
            value="Neutral",
            basis=BASIS_DOCUMENT,
            note=(
                f"The documents point both ways: a {positive.lower()} claim (cited) and "
                f"pressure on {display_name(weak_report.file_name)} p. {weak_page}: "
                f'"{weak_sentence[:160]}". Suggested Neutral; decide which weighs more.'
            ),
            citation=_cite(report, page_number, sentence),
        )
    chosen = positive or ("Weak" if "Weak" in found else None)
    if chosen is None:
        return Suggestion(
            field="competitive_position",
            label=label,
            value="Neutral",
            basis=BASIS_DEFAULT,
            note="The documents make no clear statement about competitive standing.",
        )
    report, page_number, sentence = found[chosen]
    return Suggestion(
        field="competitive_position",
        label=label,
        value=chosen,
        basis=BASIS_DOCUMENT,
        note=(
            "Read from the company's own description of itself. Confirm it against "
            "independent market data before relying on it."
        ),
        citation=_cite(report, page_number, sentence),
    )


def suggest_market_growth(reports: Sequence[DocumentIntelligenceReport]) -> Suggestion:
    for report, page_number, sentence in _passages(reports):
        match = _GROWTH.search(sentence)
        if match is None:
            continue
        rate = float(match.group(2)) / 100
        if match.group(1).lower() in _DECLINE_WORDS:
            rate = -rate
        return Suggestion(
            field="market_growth_pct",
            label="Market growth",
            value=rate,
            basis=BASIS_DOCUMENT,
            note="The growth rate the document states for its market.",
            citation=_cite(report, page_number, sentence),
        )
    return Suggestion(
        field="market_growth_pct",
        label="Market growth",
        value=None,
        basis=BASIS_NEEDS_INPUT,
        note="No market growth rate was found in the documents. Optional.",
    )


def _find_line(
    reports: Sequence[DocumentIntelligenceReport], labels: tuple[str, ...]
) -> tuple[DocumentIntelligenceReport, Any, float] | None:
    """First statement line whose label matches, with its first numeric value."""

    for label in labels:
        for report in reports:
            for item in report.statement_line_items:
                normalized = normalize_label(item.label)
                values = [value for value in item.parsed_values if value is not None]
                if values and (normalized == label or normalized.startswith(label + " ")):
                    return report, item, abs(values[0])
    return None


def _calculated(
    field: str,
    label: str,
    value: float,
    note: str,
    evidence: dict[str, dict[str, Any]],
    source_field: str,
) -> Suggestion:
    item = evidence.get(source_field)
    return Suggestion(
        field=field,
        label=label,
        value=value,
        basis=BASIS_CALCULATED,
        note=note,
        citation=SuggestionCitation(**{k: item[k] for k in SuggestionCitation.model_fields})
        if item
        else None,
    )


def suggest_inputs(reports: Sequence[DocumentIntelligenceReport]) -> SuggestedInputs:
    """Propose financial statements and valuation assumptions from a set of documents."""

    mapped, sources = map_financials_across(reports)
    evidence_list = build_financial_evidence(mapped, sources)
    evidence = {str(item["field"]): item for item in evidence_list}
    current, previous = mapped.current, mapped.previous

    def have(*names: str) -> bool:
        return all(name in current and name in previous for name in names)

    assumptions: list[Suggestion] = []

    def needs(field: str, label: str, note: str) -> None:
        assumptions.append(
            Suggestion(field=field, label=label, value=None, basis=BASIS_NEEDS_INPUT, note=note)
        )

    def default(field: str, label: str, value: float, note: str) -> None:
        assumptions.append(
            Suggestion(field=field, label=label, value=value, basis=BASIS_DEFAULT, note=note)
        )

    revenue = current.get("revenue", 0.0)

    if have("revenue") and previous["revenue"] > 0:
        growth = (revenue - previous["revenue"]) / previous["revenue"]
        assumptions.append(
            _calculated(
                "revenue_growth", "Revenue growth", growth,
                "Last year's actual growth. A forecast should reflect your own view, not "
                "simply repeat it.",
                evidence, "revenue",
            )
        )
    else:
        needs("revenue_growth", "Revenue growth", "Revenue for both periods was not found.")

    for field, label, numerator, note in (
        ("ebit_margin", "EBIT margin", "ebit", "Current-period operating income / revenue."),
        ("ebitda_margin", "EBITDA margin", "ebitda", "Current-period EBITDA / revenue."),
        (
            "capex_pct_revenue", "Capex (% of revenue)", "capital_expenditure",
            "Current-period capital expenditure / revenue.",
        ),
    ):
        if numerator in current and revenue > 0:
            assumptions.append(
                _calculated(field, label, current[numerator] / revenue, note, evidence, numerator)
            )
        else:
            needs(field, label, f"{label} could not be calculated from the documents.")

    if "total_debt" in current:
        item = evidence.get("total_debt")
        assumptions.append(
            Suggestion(
                field="debt",
                label="Debt",
                value=current["total_debt"],
                basis=BASIS_DOCUMENT,
                note="Total debt from the balance sheet.",
                citation=SuggestionCitation(
                    **{k: item[k] for k in SuggestionCitation.model_fields}
                )
                if item
                else None,
            )
        )
    else:
        needs("debt", "Debt", "No debt line was found on the balance sheet.")

    cash = _find_line(reports, _CASH_LABELS)
    if cash is not None:
        report, item, value = cash
        assumptions.append(
            Suggestion(
                field="cash",
                label="Cash",
                value=value,
                basis=BASIS_DOCUMENT,
                note="Cash from the balance sheet.",
                citation=_cite(report, item.source.page_number, item.source.excerpt),
            )
        )
    else:
        default("cash", "Cash", 0.0, "No cash line was found; assumed zero. Enter the real figure.")

    shares = _find_line(reports, _SHARE_LABELS)
    if shares is not None:
        report, item, value = shares
        assumptions.append(
            Suggestion(
                field="shares_outstanding",
                label="Shares outstanding",
                value=value,
                basis=BASIS_DOCUMENT,
                note="Share count as reported. Check it is in the same units as the statements.",
                citation=_cite(report, item.source.page_number, item.source.excerpt),
            )
        )
    else:
        needs(
            "shares_outstanding", "Shares outstanding",
            "No share count was found. Needed to express value per share.",
        )

    needs(
        "current_price_per_share", "Current price per share",
        "Optional. Enter the price to measure upside or downside against fair value.",
    )
    default(
        "entry_multiple", "Entry multiple (EV / EBITDA)", DEFAULT_ENTRY_MULTIPLE,
        "House default. Set this to the multiple you expect to pay.",
    )
    default(
        "exit_multiple", "Exit multiple (EV / EBITDA)", DEFAULT_ENTRY_MULTIPLE,
        "House default, equal to the entry multiple (no multiple expansion assumed).",
    )
    default("holding_period", "Holding period (years)", DEFAULT_HOLDING_PERIOD, "House default.")
    default(
        "tax_rate", "Tax rate", DEFAULT_TAX_RATE,
        "House default. Use the company's effective rate if you have it.",
    )
    default(
        "nwc_pct_revenue", "Working capital (% of revenue growth)", DEFAULT_NWC_PCT,
        "House default.",
    )

    return SuggestedInputs(
        current_financials={name: current[name] for name in STATEMENT_FIELDS if name in current},
        previous_financials={
            name: previous[name] for name in STATEMENT_FIELDS if name in previous
        },
        missing_financials=mapped.missing,
        financial_sources=[
            SuggestionCitation(**{k: item[k] for k in SuggestionCitation.model_fields})
            for item in evidence_list
        ],
        warnings=mapped.warnings,
        assumptions=assumptions,
        competitive_position=suggest_competitive_position(reports),
        market_growth_pct=suggest_market_growth(reports),
    )


__all__ = [
    "PeerInput",
    "SuggestedInputs",
    "Suggestion",
    "SuggestionCitation",
    "ValuationAssumptionInputs",
    "build_valuation_inputs",
    "suggest_competitive_position",
    "suggest_inputs",
    "suggest_market_growth",
]
