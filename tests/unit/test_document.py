from pathlib import Path
from uuid import UUID

from pe_analyst.domain.document import Document, DocumentType


def test_create_document(company_id: UUID) -> None:
    document = Document(
        company_id=company_id,
        file_name="report.pdf",
        file_path=Path("report.pdf"),
        document_type=DocumentType.ANNUAL_REPORT,
        year=2025,
        page_count=120,
    )

    assert document.page_count == 120
