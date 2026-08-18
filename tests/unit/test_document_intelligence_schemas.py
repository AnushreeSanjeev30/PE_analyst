import json
from pathlib import Path

import pytest

from pe_analyst.document_intelligence import DocumentIntelligenceReport, DocumentIntelligenceService
from pe_analyst.document_intelligence.models import ExtractedPage, ExtractedPDF, ExtractedTable
from pe_analyst.document_intelligence.schemas import SourceReferenceSchema


class FakeExtractor:
    def extract(self, path: Path) -> ExtractedPDF:
        return ExtractedPDF(
            path=path,
            page_count=2,
            pages=[
                ExtractedPage(
                    1,
                    "Consolidated Statements of Operations. Revenue and net income increased.",
                    [ExtractedTable(1, [["Revenue", "1,000", "900"]])],
                ),
                ExtractedPage(
                    2,
                    "Risk Factors. A loss of a major customer could adversely affect results.",
                ),
            ],
        )


def test_document_intelligence_report_round_trips_to_valid_json() -> None:
    result = DocumentIntelligenceService(FakeExtractor()).process("ExampleCo_2025.pdf")

    report = DocumentIntelligenceReport.from_result(result)

    payload = json.loads(report.model_dump_json())
    assert payload["file_name"] == "ExampleCo_2025.pdf"
    assert payload["page_count"] == 2
    assert payload["sections"][0]["kind"] in {"income_statement", "risk_factors"}
    assert payload["statement_line_items"][0]["source"]["page_number"] == 1
    assert isinstance(payload["document_id"], str)


def test_document_intelligence_report_rejects_an_invalid_page_number() -> None:
    with pytest.raises(ValueError, match="page_number"):
        SourceReferenceSchema(page_number=0, excerpt="text", confidence=0.5)
