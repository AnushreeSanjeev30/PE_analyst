"""Shared pytest fixtures for PE-Analyst."""

import os

# Must be set before any pe_analyst import reads the settings. Without it every API request in
# the suite tries to write an audit row to the developer's real DATABASE_URL, and waits out a
# connection timeout each time that database is not running.
os.environ["AUDIT_LOG_ENABLED"] = "false"

from collections.abc import Callable, Generator  # noqa: E402
from pathlib import Path  # noqa: E402
from uuid import UUID, uuid4  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import Engine, create_engine  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from pe_analyst.core.config import Settings  # noqa: E402
from pe_analyst.core.enums import Environment  # noqa: E402
from pe_analyst.db.base import Base  # noqa: E402
from pe_analyst.db.session import get_db_session, get_session_factory  # noqa: E402

# Every table except ``vector_chunks``, whose pgvector column type SQLite cannot create.
_SQLITE_TABLES = (
    "users",
    "audit_log",
    "deal_rooms",
    "deal_room_members",
    "documents",
    "deal_analyses",
)


def _sqlite_engine() -> Engine:
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(
        engine, tables=[Base.metadata.tables[name] for name in _SQLITE_TABLES]
    )
    return engine


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

    engine = _sqlite_engine()
    with Session(engine) as session:
        yield session
    engine.dispose()


@pytest.fixture(autouse=True)
def app_db() -> Generator[Callable[[], Session], None, None]:
    """Point the FastAPI app at a private in-memory database for every test.

    Document ownership and saved analyses live in the database, so any test that calls those
    endpoints needs one. Yields a session factory for tests that want to seed or inspect rows.
    A test may still override ``get_db_session`` itself (the auth tests do).
    """

    from pe_analyst.main import app

    engine = _sqlite_engine()

    def factory() -> Session:
        return Session(engine)

    def session_dependency() -> Generator[Session, None, None]:
        with factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = session_dependency
    app.dependency_overrides[get_session_factory] = lambda: factory
    yield factory
    app.dependency_overrides.pop(get_db_session, None)
    app.dependency_overrides.pop(get_session_factory, None)
    engine.dispose()


@pytest.fixture
def company_id() -> UUID:
    """Return a random company identifier."""
    return uuid4()


@pytest.fixture
def document_id() -> UUID:
    """Return a random document identifier."""
    return uuid4()
