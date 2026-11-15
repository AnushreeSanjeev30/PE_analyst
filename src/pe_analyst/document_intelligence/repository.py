"""Document ownership and sharing: who may read which document.

The extracted report stays on disk (``DocumentReportStore``); this table decides who may see it.
A document is readable by the user who uploaded it, by everyone on the deal room it is filed
in, and by an admin. A document with no row here is visible to nobody, so anything written
before ownership existed is hidden rather than leaked.
"""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings
from pe_analyst.db.models import DocumentModel
from pe_analyst.deal_rooms.repository import ADMIN_ROLE, accessible_room_ids

from .schemas import DocumentIntelligenceReport
from .storage import DocumentReportStore


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(
        self,
        report: DocumentIntelligenceReport,
        owner_id: str,
        deal_room_id: str | None = None,
    ) -> None:
        self.session.merge(
            DocumentModel(
                id=report.document_id,
                owner_id=owner_id,
                file_name=report.file_name,
                page_count=report.page_count,
                deal_room_id=deal_room_id,
            )
        )
        self.session.commit()

    def visible(
        self, user: UserPublic, *, deal_room_id: str | None = None
    ) -> list[DocumentModel]:
        """Documents ``user`` may read, most recently uploaded first.

        ``deal_room_id`` narrows the result to one room (which the caller must already have
        checked the user can access).
        """

        statement = select(DocumentModel).order_by(DocumentModel.created_at.desc())
        if user.role != ADMIN_ROLE:
            rooms = accessible_room_ids(self.session, user)
            statement = statement.where(
                or_(DocumentModel.owner_id == user.id, DocumentModel.deal_room_id.in_(rooms))
            )
        if deal_room_id is not None:
            statement = statement.where(DocumentModel.deal_room_id == deal_room_id)
        return list(self.session.execute(statement).scalars())

    def visible_ids(self, user: UserPublic) -> list[str]:
        return [document.id for document in self.visible(user)]

    def get(self, document_id: str, user: UserPublic) -> DocumentModel | None:
        """The ownership row, or None when it doesn't exist or ``user`` may not read it."""

        document = self.session.get(DocumentModel, document_id)
        if document is None:
            return None
        if user.role == ADMIN_ROLE or document.owner_id == user.id:
            return document
        if document.deal_room_id is not None and document.deal_room_id in accessible_room_ids(
            self.session, user
        ):
            return document
        return None

    def can_read(self, document_id: str, user: UserPublic) -> bool:
        return self.get(document_id, user) is not None

    def file_in_room(self, document: DocumentModel, deal_room_id: str | None) -> None:
        """Move a document into a deal room, or out of every room with ``None``."""

        document.deal_room_id = deal_room_id
        self.session.commit()


def load_visible_report(
    document_id: str, user: UserPublic, session: Session, settings: Settings
) -> DocumentIntelligenceReport | None:
    """The stored report, or None when it doesn't exist *or* the user may not read it.

    Both cases look the same to the caller on purpose: a 404 must not reveal that another
    user's document exists.
    """

    if not DocumentRepository(session).can_read(document_id, user):
        return None
    return DocumentReportStore.load(document_id, settings)


__all__ = ["ADMIN_ROLE", "DocumentRepository", "load_visible_report"]
