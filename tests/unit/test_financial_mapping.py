import pytest

from pe_analyst.document_intelligence.financial_mapping import (
    STATEMENT_FIELDS,
    map_financial_statements,
)
from pe_analyst.document_intelligence.models import SectionKind
from pe_analyst.document_intelligence.schemas import (
    DocumentIntelligenceReport,
    DocumentSectionSchema,
    SourceReferenceSchema,
    StatementLineItemSchema,
)

ROWS = [
    (SectionKind.INCOME_STATEMENT, "Total revenues", [1000.0, 900.0]),
    (SectionKind.INCOME_STATEMENT, "Cost of revenue", [600.0, 560.0]),
    (SectionKind.INCOME_STATEMENT, "Sales and marketing", [120.0, 110.0]),
    (SectionKind.INCOME_STATEMENT, "Operating income", [150.0, 130.0]),
    (SectionKind.INCOME_STATEMENT, "Interest expense", [-20.0, -22.0]),
    (SectionKind.INCOME_STATEMENT, "Net income", [100.0, 85.0]),
    (SectionKind.INCOME_STATEMENT, "Net income per share - diluted", [10.0, 8.5]),
    (SectionKind.BALANCE_SHEET, "Inventories", [50.0, 45.0]),
    (SectionKind.BALANCE_SHEET, "Total current assets", [200.0, 180.0]),
    (SectionKind.BALANCE_SHEET, "Total assets", [1000.0, 900.0]),
    (SectionKind.BALANCE_SHEET, "Total current liabilities", [180.0, 170.0]),
    (SectionKind.BALANCE_SHEET, "Current portion of long-term debt", [20.0, 10.0]),
    (SectionKind.BALANCE_SHEET, "Long-term debt", [180.0, 200.0]),
    (SectionKind.BALANCE_SHEET, "Total stockholders’ equity", [400.0, 350.0]),
    (SectionKind.CASH_FLOW_STATEMENT, "Depreciation and amortization", [70.0, 60.0]),
    (SectionKind.CASH_FLOW_STATEMENT, "Net cash provided by operating activities", [140.0, 120.0]),
    (SectionKind.CASH_FLOW_STATEMENT, "Purchases of property and equipment", [-40.0, -35.0]),
]


def _report(rows: list[tuple[SectionKind, str, list[float]]] = ROWS) -> DocumentIntelligenceReport:
    reference = SourceReferenceSchema(
        page_number=3,
        excerpt="Consolidated Statements of Operations (in millions)",
        confidence=0.85,
    )
    return DocumentIntelligenceReport(
        document_id="doc",
        file_name="annual.pdf",
        page_count=5,
        sections=[
            DocumentSectionSchema(
                kind=SectionKind.INCOME_STATEMENT, title="Income", pages=[3], references=[reference]
            )
        ],
        statement_line_items=[
            StatementLineItemSchema(
                statement=kind,
                label=label,
                raw_values=[str(value) for value in values],
                parsed_values=values,
                source=reference,
            )
            for kind, label, values in rows
        ],
        risk_factors=[],
        notes=[],
        management_discussion=[],
        industry_evidence=[],
        warnings=[],
    )


def test_maps_rows_by_synonym_with_documented_derivations() -> None:
    mapped = map_financial_statements(_report())

    current, previous = mapped.statements()
    assert mapped.missing == []
    assert current.revenue == 1000.0 and previous.revenue == 900.0
    assert current.net_income == 100.0  # not the per-share row
    assert current.cost_of_goods_sold == 600.0  # "sales and marketing" is not revenue
    assert current.capital_expenditure == 40.0 and current.interest_expense == 20.0
    assert current.total_debt == 200.0 and previous.total_debt == 210.0
    assert current.ebitda == 220.0 and previous.ebitda == 190.0
    assert current.shareholders_equity == 400.0
    assert mapped.unit_multiplier == 1e6
    assert mapped.source_pages["revenue"] == 3


def test_missing_fields_are_reported_not_invented() -> None:
    rows = [row for row in ROWS if row[1] != "Total assets"]
    mapped = map_financial_statements(_report(rows))

    assert mapped.missing == ["total_assets"]
    with pytest.raises(ValueError, match="total_assets"):
        mapped.statements()

    current, _ = mapped.statements(
        {"current": {"total_assets": 1000.0}, "previous": {"total_assets": 900.0}}
    )
    assert current.total_assets == 1000.0


def test_every_statement_field_has_a_mapping_path() -> None:
    mapped = map_financial_statements(_report())

    assert set(mapped.current) == set(STATEMENT_FIELDS)
