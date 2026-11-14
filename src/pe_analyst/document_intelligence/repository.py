"""Document ownership: which user uploaded which document.

The extracted report stays on disk (``DocumentReportStore``); this table decides who may see it.
A document with no ownership row is visible to nobody, so anything written before ownership
existed is hidden rather than leaked.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings
from pe_analyst.db.models import DocumentModel

from .schemas import DocumentIntelligenceReport
from .storage import DocumentReportStore

ADMIN_ROLE = "admin"


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def record(self, report: DocumentIntelligenceReport, owner_id: str) -> None:
        self.session.merge(
            DocumentModel(
                id=report.document_id,
                owner_id=owner_id,
                file_name=report.file_name,
                page_count=report.page_count,
            )
        )
        self.session.commit()

    def visible_ids(self, user: UserPublic) -> list[str]:
        """Ids of the documents ``user`` may read, most recently uploaded first."""

        statement = select(DocumentModel.id).order_by(DocumentModel.created_at.desc())
        if user.role != ADMIN_ROLE:
            statement = statement.where(DocumentModel.owner_id == user.id)
        return list(self.session.execute(statement).scalars())

    def can_read(self, document_id: str, user: UserPublic) -> bool:
        document = self.session.get(DocumentModel, document_id)
        if document is None:
            return False
        return user.role == ADMIN_ROLE or document.owner_id == user.id


def load_visible_report(
    document_id: str, user: UserPublic, session: Session, settings: Settings
) -> DocumentIntelligenceReport | None:
    """The stored report, or None when it doesn't exist *or* belongs to someone else.

    Both cases look the same to the caller on purpose: a 404 must not reveal that another
    user's document exists.
    """

    if not DocumentRepository(session).can_read(document_id, user):
        return None
    return DocumentReportStore.load(document_id, settings)


__all__ = ["ADMIN_ROLE", "DocumentRepository", "load_visible_report"]
