"""Engine/session construction for the FastAPI dependency graph."""

from __future__ import annotations

from collections.abc import Callable, Generator
from typing import Any

from fastapi import Depends
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from pe_analyst.core.config import Settings, get_settings

SessionFactory = Callable[[], Session]

_engines: dict[str, Engine] = {}


def get_engine(settings: Settings) -> Engine:
    """Return a process-wide cached engine for the given database URL."""

    engine = _engines.get(settings.database_url)
    if engine is None:
        connect_args: dict[str, Any] = {}
        if settings.database_url.startswith("postgresql"):
            # Without this an unreachable database blocks every request indefinitely.
            connect_args["connect_timeout"] = settings.db_connect_timeout_seconds
        engine = create_engine(settings.database_url, connect_args=connect_args)
        _engines[settings.database_url] = engine
    return engine


def get_db_session(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> Generator[Session, None, None]:
    """FastAPI dependency yielding a request-scoped session."""

    engine = get_engine(settings)
    with Session(engine) as session:
        yield session


def get_session_factory(
    settings: Settings = Depends(get_settings),  # noqa: B008
) -> SessionFactory:
    """FastAPI dependency for work that outlives the request (background analysis runs)."""

    engine = get_engine(settings)
    return lambda: Session(engine)


__all__ = ["SessionFactory", "get_db_session", "get_engine", "get_session_factory"]
