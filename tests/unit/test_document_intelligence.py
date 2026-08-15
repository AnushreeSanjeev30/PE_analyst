from pathlib import Path

from pe_analyst.document_intelligence import (
    DocumentIntelligenceService,
    ExtractedPage,
    ExtractedPDF,
    ExtractedTable,
    SectionKind,
)


class FakeExtractor:
    def extract(self, path: Path) -> ExtractedPDF:
        return ExtractedPDF(
            path=path,
            page_count=3,
            pages=[
                ExtractedPage(
                    1,
                    "Consolidated Statements of Operations. Revenue and net income increased.",
                    [ExtractedTable(1, [["Revenue", "1,000", "900"], ["Net income", "100", "80"]])],
                ),
                ExtractedPage(
                    2,
                    (
                        "Risk Factors. A loss of a major customer could adversely affect "
                        "operating results."
                    ),
                ),
                ExtractedPage(
                    3,
                    (
                        "Management's Discussion and Analysis. Market demand is growing. "
                        "Competition remains intense. Management expects sales capacity to expand."
                    ),
                ),
            ],
            metadata={"/Title": "ExampleCo Annual Report"},
        )


def test_document_intelligence_extracts_provenance_and_structured_candidates() -> None:
    result = DocumentIntelligenceService(FakeExtractor()).process("ExampleCo_2025.pdf")

    assert result.page_count == 3
    assert any(section.kind == SectionKind.INCOME_STATEMENT for section in result.sections)
    assert len(result.statement_line_items) == 2
    assert result.statement_line_items[0].source.page_number == 1
    assert result.risk_factors[0].source.page_number == 2
    assert result.management_discussion[0].page_number == 3


def test_document_intelligence_builds_industry_evidence_from_document_text() -> None:
    result = DocumentIntelligenceService(FakeExtractor()).process("ExampleCo_2025.pdf")

    assert {item["topic"] for item in result.industry_evidence} == {
        "market",
        "competition",
        "management",
    }
    assert all(item["page_number"] == 3 for item in result.industry_evidence)
