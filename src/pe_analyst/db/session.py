"""Engine/session construction for the FastAPI dependency graph."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from pe_analyst.core.config import Settings, get_settings

_engines: dict[str, Engine] = {}


def get_engine(settings: Settings) -> Engine:
    """Return a process-wide cached engine for the given database URL."""

    engine = _engines.get(settings.database_url)
    if engine is None:
        engine = create_engine(settings.database_url)
        _engines[settings.database_url] = engine
    return engine


def get_db_session(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""

    engine = get_engine(settings)
    with Session(engine) as session:
        yield session


__all__ = ["get_db_session", "get_engine"]
