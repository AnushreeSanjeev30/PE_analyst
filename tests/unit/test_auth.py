import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pe_analyst.auth.dependencies import require_role
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.db.session import get_db_session
from pe_analyst.main import app


def _client(test_settings: Settings, db_session: Session) -> TestClient:
    app.dependency_overrides[get_settings] = lambda: test_settings
    app.dependency_overrides[get_db_session] = lambda: db_session
    return TestClient(app)


def test_register_then_login_returns_a_bearer_token(
    test_settings: Settings, db_session: Session
) -> None:
    client = _client(test_settings, db_session)
    try:
        register_response = client.post(
            "/api/v1/auth/register",
            json={"email": "analyst@example.com", "password": "correct-horse-battery"},
        )
        assert register_response.status_code == 201
        assert register_response.json()["role"] == "analyst"

        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "analyst@example.com", "password": "correct-horse-battery"},
        )
        assert login_response.status_code == 200
        body = login_response.json()
        assert body["token_type"] == "bearer"
        assert body["access_token"]
    finally:
        app.dependency_overrides.clear()


def test_register_rejects_a_duplicate_email(test_settings: Settings, db_session: Session) -> None:
    client = _client(test_settings, db_session)
    try:
        payload = {"email": "analyst@example.com", "password": "correct-horse-battery"}
        client.post("/api/v1/auth/register", json=payload)

        response = client.post("/api/v1/auth/register", json=payload)

        assert response.status_code == 409
    finally:
        app.dependency_overrides.clear()


def test_login_rejects_an_incorrect_password(
    test_settings: Settings, db_session: Session
) -> None:
    client = _client(test_settings, db_session)
    try:
        client.post(
            "/api/v1/auth/register",
            json={"email": "analyst@example.com", "password": "correct-horse-battery"},
        )

        response = client.post(
            "/api/v1/auth/token",
            data={"username": "analyst@example.com", "password": "wrong-password"},
        )

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_protected_route_rejects_a_missing_token(
    test_settings: Settings, db_session: Session
) -> None:
    client = _client(test_settings, db_session)
    try:
        response = client.get("/api/v1/documents/some-id")

        assert response.status_code == 401
    finally:
        app.dependency_overrides.clear()


def test_issued_token_authorizes_a_protected_route(
    test_settings: Settings, db_session: Session
) -> None:
    client = _client(test_settings, db_session)
    try:
        client.post(
            "/api/v1/auth/register",
            json={"email": "analyst@example.com", "password": "correct-horse-battery"},
        )
        login_response = client.post(
            "/api/v1/auth/token",
            data={"username": "analyst@example.com", "password": "correct-horse-battery"},
        )
        token = login_response.json()["access_token"]

        response = client.get(
            "/api/v1/documents/unknown-id", headers={"Authorization": f"Bearer {token}"}
        )

        # 404 (not 401) proves the token was accepted and the request reached the route.
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


def test_require_role_allows_a_matching_role() -> None:
    checker = require_role("admin", "analyst")

    result = checker(UserPublic(id="1", email="a@example.com", role="analyst"))

    assert result.role == "analyst"


def test_require_role_rejects_a_non_matching_role() -> None:
    checker = require_role("admin")

    with pytest.raises(HTTPException) as excinfo:
        checker(UserPublic(id="1", email="a@example.com", role="analyst"))

    assert excinfo.value.status_code == 403
