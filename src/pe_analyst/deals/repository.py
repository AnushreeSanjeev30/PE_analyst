"""Persistence for deal-analysis runs, so a report outlives the request that produced it.

An analysis is readable by the user who ran it, by everyone on the deal room it is filed in,
and by an admin. Only the person who ran it (or an admin) can delete it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import or_, select, update
from sqlalchemy.orm import Session, defer

from pe_analyst.auth.models import UserPublic
from pe_analyst.db.models import DealAnalysisModel
from pe_analyst.deal_rooms.repository import ADMIN_ROLE, accessible_room_ids

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
        deal_room_id: str | None = None,
    ) -> DealAnalysisModel:
        analysis = DealAnalysisModel(
            owner_id=owner_id,
            company_name=company_name,
            document_id=document_id,
            deal_room_id=deal_room_id,
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
        """The analysis, or None when it doesn't exist or the user may not read it."""

        analysis = self.session.get(DealAnalysisModel, analysis_id)
        if analysis is None:
            return None
        if user.role == ADMIN_ROLE or analysis.owner_id == user.id:
            return analysis
        if analysis.deal_room_id is not None and analysis.deal_room_id in accessible_room_ids(
            self.session, user
        ):
            return analysis
        return None

    def list_for(
        self, user: UserPublic, *, deal_room_id: str | None = None
    ) -> list[DealAnalysisModel]:
        """Analyses the caller may read, newest first, without loading each full report.

        ``deal_room_id`` narrows the list to one deal (which the caller must already have
        checked the user can access).
        """

        statement = (
            select(DealAnalysisModel)
            .options(defer(DealAnalysisModel.report), defer(DealAnalysisModel.request))
            .order_by(DealAnalysisModel.created_at.desc())
        )
        if user.role != ADMIN_ROLE:
            rooms = accessible_room_ids(self.session, user)
            statement = statement.where(
                or_(
                    DealAnalysisModel.owner_id == user.id,
                    DealAnalysisModel.deal_room_id.in_(rooms),
                )
            )
        if deal_room_id is not None:
            statement = statement.where(DealAnalysisModel.deal_room_id == deal_room_id)
        return list(self.session.execute(statement).scalars())

    def delete(self, analysis_id: str, user: UserPublic) -> bool:
        """Delete an analysis. Team members can read each other's runs but not delete them."""

        analysis = self.get(analysis_id, user)
        if analysis is None:
            return False
        if user.role != ADMIN_ROLE and analysis.owner_id != user.id:
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
