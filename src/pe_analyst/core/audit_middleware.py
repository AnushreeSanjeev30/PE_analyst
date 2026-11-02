"""Best-effort request audit logging.

Writes one row per request to ``audit_log`` after the response is produced. Never blocks or
fails a request: any logging error (including "no database configured/reachable", the common
case in local dev and the test suite) is swallowed and logged at debug level -- the same
never-break-the-primary-path rule already used for RAG ingestion during document upload.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from pe_analyst.auth.security import InvalidTokenError, decode_access_token
from pe_analyst.core.config import get_settings
from pe_analyst.core.logging import get_logger
from pe_analyst.db.models import AuditLogModel
from pe_analyst.db.session import get_engine

logger = get_logger(__name__)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        self._record(request, response)
        return response

    def _record(self, request: Request, response: Response) -> None:
        settings = get_settings()
        try:
            engine = get_engine(settings)
            with Session(engine) as session:
                session.add(
                    AuditLogModel(
                        user_id=self._resolve_user_id(request),
                        method=request.method,
                        path=request.url.path,
                        status_code=response.status_code,
                    )
                )
                session.commit()
        except Exception as error:  # noqa: BLE001 - audit logging must never break a response
            logger.debug(
                "Audit logging skipped for %s %s: %s", request.method, request.url.path, error
            )

    @staticmethod
    def _resolve_user_id(request: Request) -> str | None:
        header = request.headers.get("authorization", "")
        if not header.lower().startswith("bearer "):
            return None
        settings = get_settings()
        try:
            payload = decode_access_token(header.split(" ", 1)[1], settings)
        except InvalidTokenError:
            return None
        return payload.subject


__all__ = ["AuditLoggingMiddleware"]
