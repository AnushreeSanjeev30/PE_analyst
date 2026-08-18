"""FastAPI application entry point. Run with: uvicorn pe_analyst.main:app"""

from __future__ import annotations

from fastapi import FastAPI

from pe_analyst.core.config import get_settings
from pe_analyst.core.logging import configure_logging
from pe_analyst.document_intelligence.api import router as document_intelligence_router

settings = get_settings()
configure_logging(settings)

app = FastAPI(title=settings.app_name)
app.include_router(document_intelligence_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok"}


__all__ = ["app"]
