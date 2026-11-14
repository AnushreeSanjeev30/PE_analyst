"""Persistence for deal-analysis runs, so a report outlives the request that produced it."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session, defer

from pe_analyst.auth.models import UserPublic
from pe_analyst.db.models import DealAnalysisModel
from pe_analyst.document_intelligence.repository import ADMIN_ROLE

STATUS_PENDING = "pending"
STATUS_RUNNING = "running"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"

_UNFINISHED = (STATUS_PENDING, STATUS_RUNNING)


def _now() -> datetime:
    return datetime.now(UTC)


class DealAnalysisRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        owner_id: str,
        company_name: str,
        document_id: str | None,
        request: dict[str, Any],
        analysis_id: str | None = None,
    ) -> DealAnalysisModel:
        analysis = DealAnalysisModel(
            owner_id=owner_id,
            company_name=company_name,
            document_id=document_id,
            request=request,
            status=STATUS_PENDING,
        )
        if analysis_id is not None:
            analysis.id = analysis_id
        self.session.add(analysis)
        self.session.commit()
        self.session.refresh(analysis)
        return analysis

    def mark_running(self, analysis_id: str) -> None:
        self._update(analysis_id, status=STATUS_RUNNING)

    def finish(
        self,
        analysis_id: str,
        *,
        status: str,
        report: dict[str, Any] | None,
        recommendation: str | None,
        error: str | None,
    ) -> None:
        self._update(
            analysis_id,
            status=status,
            report=report,
            recommendation=recommendation,
            error=error,
            completed_at=_now(),
        )

    def get(self, analysis_id: str, user: UserPublic) -> DealAnalysisModel | None:
        """The analysis, or None when it doesn't exist or belongs to someone else."""

        analysis = self.session.get(DealAnalysisModel, analysis_id)
        if analysis is None:
            return None
        if user.role != ADMIN_ROLE and analysis.owner_id != user.id:
            return None
        return analysis

    def list_for(self, user: UserPublic) -> list[DealAnalysisModel]:
        """The caller's analyses, newest first, without loading each full report."""

        statement = (
            select(DealAnalysisModel)
            .options(defer(DealAnalysisModel.report), defer(DealAnalysisModel.request))
            .order_by(DealAnalysisModel.created_at.desc())
        )
        if user.role != ADMIN_ROLE:
            statement = statement.where(DealAnalysisModel.owner_id == user.id)
        return list(self.session.execute(statement).scalars())

    def delete(self, analysis_id: str, user: UserPublic) -> bool:
        analysis = self.get(analysis_id, user)
        if analysis is None:
            return False
        self.session.delete(analysis)
        self.session.commit()
        return True

    def fail_unfinished(self, reason: str) -> int:
        """Mark every pending/running analysis failed. Returns how many were changed.

        Runs execute inside the API process, so any still unfinished when the process starts
        were cut off by a restart and will never complete on their own.
        """

        result = self.session.execute(
            update(DealAnalysisModel)
            .where(DealAnalysisModel.status.in_(_UNFINISHED))
            .values(status=STATUS_FAILED, error=reason, completed_at=_now())
        )
        self.session.commit()
        return int(getattr(result, "rowcount", 0) or 0)

    def _update(self, analysis_id: str, **values: Any) -> None:
        self.session.execute(
            update(DealAnalysisModel).where(DealAnalysisModel.id == analysis_id).values(**values)
        )
        self.session.commit()


__all__ = [
    "STATUS_COMPLETED",
    "STATUS_FAILED",
    "STATUS_PENDING",
    "STATUS_RUNNING",
    "DealAnalysisRepository",
]
