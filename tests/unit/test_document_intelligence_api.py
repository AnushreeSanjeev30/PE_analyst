import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from pe_analyst.core.config import Settings, get_settings
from pe_analyst.main import app


def _blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _client(test_settings: Settings) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: test_settings
    return TestClient(app)


def test_upload_document_returns_a_validated_report(test_settings: Settings) -> None:
    client = _client(test_settings)
    try:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("Annual_Report.pdf", _blank_pdf_bytes(), "application/pdf")},
        )

        assert response.status_code == 201
        body = response.json()
        assert body["file_name"].endswith("Annual_Report.pdf")
        assert body["page_count"] == 1
        assert "No extractable text found" in " ".join(body["warnings"])
        assert list(test_settings.upload_dir.glob("*Annual_Report.pdf"))
    finally:
        app.dependency_overrides.clear()


def test_upload_document_rejects_non_pdf_uploads(test_settings: Settings) -> None:
    client = _client(test_settings)
    try:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("notes.txt", b"just text", "text/plain")},
        )

        assert response.status_code == 415
    finally:
        app.dependency_overrides.clear()


def test_upload_document_rejects_oversized_files(test_settings: Settings) -> None:
    test_settings = Settings(
        app_env=test_settings.app_env,
        upload_dir=test_settings.upload_dir,
        processed_data_dir=test_settings.processed_data_dir,
        max_upload_size_mb=1,
    )
    client = _client(test_settings)
    try:
        oversized = b"%PDF-1.4\n" + b"0" * (2 * 1024 * 1024)
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("Big_CIM.pdf", oversized, "application/pdf")},
        )

        assert response.status_code == 413
    finally:
        app.dependency_overrides.clear()
