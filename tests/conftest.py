"""Shared pytest fixtures for PE-Analyst."""

from collections.abc import Generator
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from pe_analyst.core.config import Settings
from pe_analyst.core.enums import Environment
from pe_analyst.db.base import Base


@pytest.fixture
def test_settings(tmp_path: Path) -> Settings:
    """Return isolated application settings for tests."""

    return Settings(
        app_env=Environment.TESTING,
        debug=True,
        upload_dir=tmp_path / "uploads",
        processed_data_dir=tmp_path / "processed",
        openai_api_key=None,
        groq_api_key=None,
        xai_api_key=None,
        anthropic_api_key=None,
        gemini_api_key=None,
        llm_provider="groq",
        llm_log_dir=None,
        market_data_provider="unconfigured",
        market_data_cache_dir=tmp_path / "market_cache",
    )


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """An isolated in-memory SQLite session for DB-backed unit tests.

    No Docker/Postgres required: this exercises the same SQLAlchemy models (users, audit log)
    against SQLite, which is sufficient for anything that doesn't touch the pgvector-typed
    ``vector_chunks`` table (that table is only exercised by PgVectorStore's own tests, which
    self-skip when a real Postgres isn't reachable).
    """

    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    tables = [Base.metadata.tables["users"], Base.metadata.tables["audit_log"]]
    Base.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture
def company_id() -> UUID:
    """Return a random company identifier."""
    return uuid4()


@pytest.fixture
def document_id() -> UUID:
    """Return a random document identifier."""
    return uuid4()
