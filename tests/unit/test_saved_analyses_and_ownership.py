"""Saved analyses, background runs, and per-user isolation of documents and reports."""

from __future__ import annotations

import io
from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from sqlalchemy.orm import Session
from tests.unit.test_deals_api import _request_body

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.core.enums import Environment
from pe_analyst.deals.api import get_narrator
from pe_analyst.deals.repository import DealAnalysisRepository
from pe_analyst.main import app

ALICE = UserPublic(id="alice", email="alice@example.com", role="analyst")
BOB = UserPublic(id="bob", email="bob@example.com", role="analyst")


def _blank_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _act_as(user: UserPublic) -> None:
    app.dependency_overrides[get_current_user] = lambda: user


@pytest.fixture
def client(test_settings: Settings) -> Iterator[TestClient]:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_narrator] = lambda: None
    _act_as(ALICE)
    try:
        yield TestClient(app)
    finally:
        for dependency in (get_settings, get_narrator, get_current_user):
            app.dependency_overrides.pop(dependency, None)


# ---------------------------------------------------------------------------
# Saved analyses
# ---------------------------------------------------------------------------


def test_background_analysis_is_saved_and_fetchable(client: TestClient) -> None:
    started = client.post("/api/v1/deals/analyses", json=_request_body())

    assert started.status_code == 202, started.text
    analysis_id = started.json()["id"]

    # TestClient runs background tasks before returning, so the run has finished by now.
    record = client.get(f"/api/v1/deals/analyses/{analysis_id}").json()
    assert record["status"] == "completed"
    assert record["recommendation"] in {"BUY", "HOLD", "REJECT"}
    assert record["report"]["run_id"] == analysis_id
    assert record["report"]["final_recommendation"] == record["recommendation"]
    assert record["report"]["ic_decision"]["explanation"]["drivers"]

    listing = client.get("/api/v1/deals/analyses").json()
    assert [item["id"] for item in listing] == [analysis_id]
    assert "report" not in listing[0]


def test_blocking_analysis_is_saved_under_its_run_id(client: TestClient) -> None:
    report = client.post("/api/v1/deals/analyze", json=_request_body()).json()

    saved = client.get(f"/api/v1/deals/analyses/{report['run_id']}")

    assert saved.status_code == 200
    assert saved.json()["report"]["final_recommendation"] == report["final_recommendation"]


def test_invalid_request_is_rejected_before_a_run_is_created(client: TestClient) -> None:
    body = _request_body(document_id="missing", industry_name="Vertical Software")
    del body["industry_inputs"]

    response = client.post("/api/v1/deals/analyses", json=body)

    assert response.status_code == 404
    assert client.get("/api/v1/deals/analyses").json() == []


def test_a_crashed_run_is_recorded_as_failed(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    def explode(*args: object, **kwargs: object) -> None:
        raise RuntimeError("engine fell over")

    monkeypatch.setattr("pe_analyst.deals.api.run_deal_analysis", explode)

    analysis_id = client.post("/api/v1/deals/analyses", json=_request_body()).json()["id"]

    record = client.get(f"/api/v1/deals/analyses/{analysis_id}").json()
    assert record["status"] == "failed"
    assert "engine fell over" in record["error"]
    assert record["report"] is None


def test_unfinished_runs_are_failed_on_restart(app_db: Callable[[], Session]) -> None:
    with app_db() as session:
        repository = DealAnalysisRepository(session)
        analysis = repository.create(
            owner_id="alice", company_name="ExampleCo", document_id=None, request={}
        )
        repository.mark_running(analysis.id)

        assert repository.fail_unfinished("restarted") == 1

        session.expire_all()
        reloaded = repository.get(analysis.id, ALICE)
        assert reloaded is not None
        assert reloaded.status == "failed"
        assert reloaded.error == "restarted"


def test_analysis_can_be_deleted(client: TestClient) -> None:
    analysis_id = client.post("/api/v1/deals/analyses", json=_request_body()).json()["id"]

    assert client.delete(f"/api/v1/deals/analyses/{analysis_id}").status_code == 204
    assert client.get(f"/api/v1/deals/analyses/{analysis_id}").status_code == 404


# ---------------------------------------------------------------------------
# Per-user isolation
# ---------------------------------------------------------------------------


def test_one_user_cannot_see_another_users_analysis(client: TestClient) -> None:
    analysis_id = client.post("/api/v1/deals/analyses", json=_request_body()).json()["id"]

    _act_as(BOB)

    assert client.get("/api/v1/deals/analyses").json() == []
    assert client.get(f"/api/v1/deals/analyses/{analysis_id}").status_code == 404
    assert client.delete(f"/api/v1/deals/analyses/{analysis_id}").status_code == 404


def test_one_user_cannot_see_or_use_another_users_document(client: TestClient) -> None:
    upload = client.post(
        "/api/v1/documents/upload",
        files={"file": ("Alice_CIM.pdf", _blank_pdf_bytes(), "application/pdf")},
    )
    document_id = upload.json()["document_id"]
    assert [item["document_id"] for item in client.get("/api/v1/documents").json()] == [
        document_id
    ]

    _act_as(BOB)

    assert client.get("/api/v1/documents").json() == []
    assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
    question = {"question": "What is the EBITDA?", "document_id": document_id}
    assert client.post("/api/v1/rag/query", json=question).status_code == 404
    body = _request_body(document_id=document_id, industry_name="Vertical Software")
    del body["industry_inputs"]
    assert client.post("/api/v1/deals/analyze", json=body).status_code == 404


def test_admin_can_see_every_users_work(client: TestClient) -> None:
    analysis_id = client.post("/api/v1/deals/analyses", json=_request_body()).json()["id"]

    _act_as(UserPublic(id="root", email="root@example.com", role="admin"))

    assert [item["id"] for item in client.get("/api/v1/deals/analyses").json()] == [analysis_id]


# ---------------------------------------------------------------------------
# Production secret key
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "secret_key",
    ["dev-only-insecure-secret-change-me", "change-me-to-a-long-random-value", "too-short"],
)
def test_production_refuses_a_weak_secret_key(secret_key: str) -> None:
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings(app_env=Environment.PRODUCTION, secret_key=secret_key)


def test_production_accepts_a_strong_secret_key() -> None:
    settings = Settings(app_env=Environment.PRODUCTION, secret_key="k" * 48)

    assert settings.is_production


def test_development_still_starts_with_the_default_secret_key() -> None:
    settings = Settings(
        app_env=Environment.DEVELOPMENT, secret_key="dev-only-insecure-secret-change-me"
    )

    assert settings.is_development
