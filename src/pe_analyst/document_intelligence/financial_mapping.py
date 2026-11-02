"""Maps extracted statement rows onto the ``FinancialStatement`` the agents consume.

Statement tables arrive as label + values rows (``StatementLineItemSchema``). This module finds
the row for each ``FinancialStatement`` field by label synonyms and reads the first two numeric
columns as the current and prior period -- the column order used by 10-Ks and most annual
reports. Every mapped value keeps the page it came from.

Nothing is invented: a field that can't be found is reported in ``missing`` and
:meth:`MappedFinancials.statements` refuses to build statements until it is supplied through
``overrides``. The two narrow exceptions are documented derivations (EBITDA = operating income +
D&A; total debt = sum of its reported components) and inventory, which defaults to zero with a
warning because many service businesses genuinely carry none.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, fields

from pe_analyst.engines.financial.models import FinancialStatement

from .schemas import DocumentIntelligenceReport, StatementLineItemSchema

STATEMENT_FIELDS = [item.name for item in fields(FinancialStatement)]

# Ordered most-specific first; the first synonym that matches a row wins.
FIELD_SYNONYMS: dict[str, tuple[str, ...]] = {
    "revenue": (
        "total revenues", "total revenue", "total net revenue", "total net sales", "net revenues",
        "net revenue", "net sales", "revenues", "revenue", "sales",
    ),
    "cost_of_goods_sold": (
        "total cost of revenues", "total cost of revenue", "cost of revenues", "cost of revenue",
        "cost of goods sold", "cost of sales",
    ),
    "ebitda": ("ebitda", "adjusted ebitda"),
    "ebit": (
        "operating income", "income from operations", "operating profit", "ebit",
        "operating income (loss)",
    ),
    "net_income": (
        "net income", "net earnings", "net income (loss)", "net loss", "profit for the year",
        "net income attributable to common stockholders",
    ),
    "operating_cash_flow": (
        "net cash provided by operating activities",
        "net cash provided by (used in) operating activities",
        "net cash from operating activities",
        "cash generated from operations",
        "net cash generated from operating activities",
    ),
    "capital_expenditure": (
        "capital expenditures", "purchases of property and equipment",
        "purchases of property, plant and equipment", "purchase of property and equipment",
        "additions to property and equipment", "payments for acquisition of property",
    ),
    "total_assets": ("total assets",),
    "shareholders_equity": (
        "total stockholders equity", "total shareholders equity", "total equity",
        "stockholders equity", "shareholders equity",
    ),
    "total_debt": ("total debt", "total borrowings"),
    "interest_expense": ("interest expense", "interest expense, net", "finance costs"),
    "current_assets": ("total current assets",),
    "inventory": ("inventories", "inventory", "inventories, net"),
    "current_liabilities": ("total current liabilities",),
}

_DEBT_COMPONENTS = (
    "long-term debt", "long term debt", "short-term debt", "short term debt",
    "current portion of long-term debt", "notes payable", "short-term borrowings",
    "long-term borrowings", "commercial paper",
)
_DEPRECIATION = ("depreciation and amortization", "depreciation & amortization", "depreciation")
_EXCLUDE = ("per share", "margin", "basic", "diluted", "%", "weighted")
_ABSOLUTE_FIELDS = {"capital_expenditure", "interest_expense"}


def normalize_label(label: str) -> str:
    text = label.lower().replace("’", "'").replace("'", "")
    text = re.sub(r"\(note \d+\)|\bnote \d+\b", "", text)
    text = re.sub(r"[^a-z0-9&,()\- ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip(" ,:")


def _numbers(item: StatementLineItemSchema) -> list[float]:
    return [value for value in item.parsed_values if value is not None]


@dataclass(slots=True)
class MappedFinancials:
    current: dict[str, float] = field(default_factory=dict)
    previous: dict[str, float] = field(default_factory=dict)
    source_pages: dict[str, int] = field(default_factory=dict)
    source_labels: dict[str, str] = field(default_factory=dict)
    missing: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    # Values stay in the document's units; ``unit_multiplier`` converts them to currency units
    # (e.g. 1e6 for statements presented "in millions").
    unit_multiplier: float = 1.0

    def statements(
        self, overrides: dict[str, dict[str, float]] | None = None
    ) -> tuple[FinancialStatement, FinancialStatement]:
        """Build (current, previous) statements; ``overrides`` = {"current": {...}, ...}."""

        overrides = overrides or {}
        current = {**self.current, **overrides.get("current", {})}
        previous = {**self.previous, **overrides.get("previous", {})}
        missing = sorted(
            {name for name in STATEMENT_FIELDS if name not in current}
            | {name for name in STATEMENT_FIELDS if name not in previous}
        )
        if missing:
            raise ValueError(
                "Could not extract these financial fields for both periods; supply them "
                f"explicitly: {', '.join(missing)}"
            )
        return FinancialStatement(**current), FinancialStatement(**previous)


def _find(items: list[StatementLineItemSchema], synonyms: tuple[str, ...]) -> (
    StatementLineItemSchema | None
):
    candidates = [
        (normalize_label(item.label), item)
        for item in items
        if _numbers(item) and not any(term in item.label.lower() for term in _EXCLUDE)
    ]
    for synonym in synonyms:
        for label, item in candidates:
            if label == synonym:
                return item
    # Prefix matching only for multi-word synonyms: "sales" must not match "sales and marketing".
    for synonym in (term for term in synonyms if " " in term):
        for label, item in candidates:
            if label.startswith(synonym + " ") or label.startswith(synonym + ","):
                return item
    return None


def _assign(mapped: MappedFinancials, name: str, item: StatementLineItemSchema) -> None:
    values = _numbers(item)
    if name in _ABSOLUTE_FIELDS:
        values = [abs(value) for value in values]
    mapped.current[name] = values[0]
    if len(values) > 1:
        mapped.previous[name] = values[1]
    mapped.source_pages[name] = item.source.page_number
    mapped.source_labels[name] = item.label


_UNITS = re.compile(r"in\s+(thousands|millions|billions)", re.IGNORECASE)
_UNIT_MULTIPLIERS = {"thousands": 1e3, "millions": 1e6, "billions": 1e9}
_STATEMENT_KINDS = {"income_statement", "balance_sheet", "cash_flow_statement"}


def detect_unit_multiplier(report: DocumentIntelligenceReport) -> float:
    """Most common "(in millions)"-style declaration on the statement pages; 1.0 if none."""

    counts: dict[float, int] = {}
    for section in report.sections:
        if section.kind.value not in _STATEMENT_KINDS:
            continue
        for reference in section.references:
            for match in _UNITS.finditer(reference.excerpt):
                multiplier = _UNIT_MULTIPLIERS[match.group(1).lower()]
                counts[multiplier] = counts.get(multiplier, 0) + 1
    return max(counts, key=lambda key: counts[key]) if counts else 1.0


def map_financial_statements(report: DocumentIntelligenceReport) -> MappedFinancials:
    items = list(report.statement_line_items)
    mapped = MappedFinancials(unit_multiplier=detect_unit_multiplier(report))

    for name, synonyms in FIELD_SYNONYMS.items():
        item = _find(items, synonyms)
        if item is not None:
            _assign(mapped, name, item)

    if "total_debt" not in mapped.current:
        components = [
            item
            for item in items
            if _numbers(item)
            and any(normalize_label(item.label).startswith(term) for term in _DEBT_COMPONENTS)
        ]
        if components:
            mapped.current["total_debt"] = sum(_numbers(item)[0] for item in components)
            if all(len(_numbers(item)) > 1 for item in components):
                mapped.previous["total_debt"] = sum(_numbers(item)[1] for item in components)
            mapped.source_pages["total_debt"] = components[0].source.page_number
            mapped.source_labels["total_debt"] = " + ".join(item.label for item in components)
            mapped.warnings.append("total_debt derived by summing reported debt components.")

    if "ebitda" not in mapped.current and "ebit" in mapped.current:
        depreciation = _find(items, _DEPRECIATION)
        if depreciation is not None:
            values = [abs(value) for value in _numbers(depreciation)]
            mapped.current["ebitda"] = mapped.current["ebit"] + values[0]
            if "ebit" in mapped.previous and len(values) > 1:
                mapped.previous["ebitda"] = mapped.previous["ebit"] + values[1]
            mapped.source_pages["ebitda"] = depreciation.source.page_number
            ebit_label = mapped.source_labels["ebit"]
            mapped.source_labels["ebitda"] = f"{ebit_label} + {depreciation.label}"
            mapped.warnings.append("ebitda derived as operating income + depreciation/amortization")

    if "inventory" not in mapped.current:
        mapped.current["inventory"] = 0.0
        mapped.previous["inventory"] = 0.0
        mapped.warnings.append("No inventory line found; assumed zero (verify for this business).")

    mapped.missing = [
        name
        for name in STATEMENT_FIELDS
        if name not in mapped.current or name not in mapped.previous
    ]
    return mapped


__all__ = [
    "FIELD_SYNONYMS",
    "MappedFinancials",
    "STATEMENT_FIELDS",
    "detect_unit_multiplier",
    "map_financial_statements",
    "normalize_label",
]
