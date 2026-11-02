import io

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
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
    app.dependency_overrides[get_current_user] = lambda: UserPublic(
        id="test-user", email="analyst@example.com", role="analyst"
    )
    return TestClient(app)


def test_query_against_an_empty_index_is_graceful(test_settings: Settings) -> None:
    client = _client(test_settings)
    try:
        response = client.post("/api/v1/rag/query", json={"question": "What is the EBITDA?"})

        assert response.status_code == 200
        body = response.json()
        assert body["confidence"] == 0.0
        assert body["citations"] == []
        assert body["warnings"]
    finally:
        app.dependency_overrides.clear()


def test_query_rejects_an_empty_question(test_settings: Settings) -> None:
    client = _client(test_settings)
    try:
        response = client.post("/api/v1/rag/query", json={"question": ""})

        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()


def test_uploading_a_document_does_not_fail_even_when_nothing_can_be_indexed(
    test_settings: Settings,
) -> None:
    client = _client(test_settings)
    try:
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("Annual_Report.pdf", _blank_pdf_bytes(), "application/pdf")},
        )

        assert response.status_code == 201
    finally:
        app.dependency_overrides.clear()
