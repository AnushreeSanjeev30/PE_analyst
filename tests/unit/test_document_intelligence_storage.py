from pe_analyst.core.config import Settings
from pe_analyst.document_intelligence.schemas import DocumentIntelligenceReport
from pe_analyst.document_intelligence.storage import DocumentReportStore


def _report(document_id: str) -> DocumentIntelligenceReport:
    return DocumentIntelligenceReport(
        document_id=document_id,
        file_name="ExampleCo.pdf",
        page_count=1,
        sections=[],
        statement_line_items=[],
        risk_factors=[],
        notes=[],
        management_discussion=[],
        industry_evidence=[],
        warnings=[],
    )


def test_save_then_load_round_trips_the_report(test_settings: Settings) -> None:
    report = _report("doc-1")

    DocumentReportStore.save(report, test_settings)
    loaded = DocumentReportStore.load("doc-1", test_settings)

    assert loaded == report


def test_load_returns_none_for_an_unknown_document(test_settings: Settings) -> None:
    assert DocumentReportStore.load("missing-doc", test_settings) is None


def test_list_all_is_empty_when_nothing_was_saved(test_settings: Settings) -> None:
    assert DocumentReportStore.list_all(test_settings) == []


def test_list_all_returns_every_saved_report(test_settings: Settings) -> None:
    DocumentReportStore.save(_report("doc-1"), test_settings)
    DocumentReportStore.save(_report("doc-2"), test_settings)

    reports = DocumentReportStore.list_all(test_settings)

    assert {report.document_id for report in reports} == {"doc-1", "doc-2"}
