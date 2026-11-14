"""FastAPI application entry point. Run with: uvicorn pe_analyst.main:app"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from pe_analyst.auth.api import router as auth_router
from pe_analyst.core.audit_middleware import AuditLoggingMiddleware
from pe_analyst.core.config import get_settings
from pe_analyst.core.logging import configure_logging, get_logger
from pe_analyst.db.session import get_engine
from pe_analyst.deals.api import router as deals_router
from pe_analyst.deals.repository import DealAnalysisRepository
from pe_analyst.document_intelligence.api import router as document_intelligence_router
from pe_analyst.rag.api import router as rag_router

settings = get_settings()
configure_logging(settings)
logger = get_logger(__name__)


def fail_interrupted_analyses() -> None:
    """Close out analyses a previous process left unfinished, so nothing polls forever.

    Assumes a single API process (the Docker image runs one uvicorn worker). With several
    workers, move analysis runs to a real job queue before relying on this.
    """

    try:
        with Session(get_engine(settings)) as session:
            count = DealAnalysisRepository(session).fail_unfinished(
                "The server restarted before this analysis finished. Run it again."
            )
        if count:
            logger.warning("Marked %d interrupted deal analyses as failed", count)
    except Exception as error:  # noqa: BLE001 - never block startup on housekeeping
        logger.warning("Could not check for interrupted deal analyses: %s", error)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    fail_interrupted_analyses()
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(AuditLoggingMiddleware)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(document_intelligence_router, prefix="/api/v1")
app.include_router(rag_router, prefix="/api/v1")
app.include_router(deals_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["app"]
