"""Upload, list, fetch and open deal documents (annual reports, CIMs, ...)."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.core.logging import get_logger
from pe_analyst.db.session import get_db_session
from pe_analyst.deal_rooms.repository import DealRoomRepository
from pe_analyst.rag.retrieval import build_retrieval_service

from .agent_inputs import display_name
from .extractor import PDFExtractionError
from .repository import DocumentRepository, load_visible_report
from .schemas import DocumentIntelligenceReport, DocumentSummary
from .service import DocumentIntelligenceService
from .storage import DocumentReportStore

router = APIRouter(prefix="/documents", tags=["document-intelligence"])
logger = get_logger(__name__)


class DealRoomAssignment(BaseModel):
    # ``None`` takes the document out of its deal room and makes it private again.
    deal_room_id: str | None = None


def _require_room(room_id: str, user: UserPublic, session: Session) -> None:
    if DealRoomRepository(session).get(room_id, user) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No deal found with id {room_id}")


@router.post(
    "/upload",
    response_model=DocumentIntelligenceReport,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an annual report, CIM, or other deal PDF for extraction",
)
async def upload_document(
    file: UploadFile,
    deal_room_id: str | None = Form(default=None),  # noqa: B008
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DocumentIntelligenceReport:
    """Persist an uploaded PDF and return its validated document-intelligence report.

    Pass ``deal_room_id`` to file the document in a deal room, which shares it with that
    deal's team. Without it the document is private to the uploader.
    """

    if deal_room_id:
        _require_room(deal_room_id, current_user, session)

    filename = file.filename or ""
    if (file.content_type or "").lower() != "application/pdf" and not filename.lower().endswith(
        ".pdf"
    ):
        raise HTTPException(
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Only PDF documents are accepted."
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Uploaded file is empty.")

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if len(payload) > max_bytes:
        raise HTTPException(
            status.HTTP_413_CONTENT_TOO_LARGE,
            f"File exceeds the {settings.max_upload_size_mb}MB upload limit.",
        )

    settings.ensure_directories()
    destination = settings.upload_dir / f"{uuid.uuid4()}_{Path(filename or 'document.pdf').name}"
    destination.write_bytes(payload)

    try:
        result = DocumentIntelligenceService().process(destination)
    except (PDFExtractionError, ValueError, FileNotFoundError) as error:
        logger.warning("Document intelligence extraction failed for %s: %s", destination, error)
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(error)) from error

    logger.info("Processed document %s (%d pages)", result.file_name, result.page_count)
    report = DocumentIntelligenceReport.from_result(result)
    DocumentReportStore.save(report, settings)
    DocumentRepository(session).record(report, current_user.id, deal_room_id or None)

    try:
        chunk_count = build_retrieval_service(settings).ingest_document(
            destination, report.document_id
        )
        logger.info("Indexed %d chunks for document %s", chunk_count, report.document_id)
    except Exception as error:  # noqa: BLE001 - indexing must never fail the upload
        logger.warning("RAG ingestion failed for document %s: %s", report.document_id, error)

    return report


@router.get(
    "",
    response_model=list[DocumentSummary],
    summary="List the documents the caller may read, most recently uploaded first",
)
async def list_documents(
    deal_room_id: str | None = None,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> list[DocumentSummary]:
    """Own documents plus those filed in the caller's deal rooms; ``deal_room_id`` narrows
    the list to one deal."""

    if deal_room_id:
        _require_room(deal_room_id, current_user, session)
    summaries = []
    for row in DocumentRepository(session).visible(current_user, deal_room_id=deal_room_id):
        report = DocumentReportStore.load(row.id, settings)
        if report is not None:
            summaries.append(
                DocumentSummary.from_report(
                    report, deal_room_id=row.deal_room_id, uploaded_at=row.created_at
                )
            )
    return summaries


@router.get(
    "/{document_id}",
    response_model=DocumentIntelligenceReport,
    summary="Fetch a previously processed document-intelligence report",
)
async def get_document(
    document_id: str,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DocumentIntelligenceReport:
    report = load_visible_report(document_id, current_user, session, settings)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No document found with id {document_id}")
    return report


@router.get(
    "/{document_id}/file",
    response_class=FileResponse,
    summary="Download the original PDF, so a citation can be opened at its page",
)
async def get_document_file(
    document_id: str,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> FileResponse:
    report = load_visible_report(document_id, current_user, session, settings)
    if report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No document found with id {document_id}")
    # ``file_name`` is the name the upload was stored under; ``.name`` keeps the lookup inside
    # the upload directory whatever that string contains.
    path = settings.upload_dir / Path(report.file_name).name
    if not path.is_file():
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "The original PDF is no longer stored. Upload the document again to view it.",
        )
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=display_name(report.file_name),
        content_disposition_type="inline",
    )


@router.put(
    "/{document_id}/deal-room",
    response_model=DocumentSummary,
    summary="File a document in a deal room (sharing it with that team), or remove it",
)
async def assign_deal_room(
    document_id: str,
    payload: DealRoomAssignment,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DocumentSummary:
    repository = DocumentRepository(session)
    row = repository.get(document_id, current_user)
    report = DocumentReportStore.load(document_id, settings) if row is not None else None
    if row is None or report is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"No document found with id {document_id}")
    # Sharing changes who can read the file, so only its uploader (or an admin) may do it.
    if current_user.role != "admin" and row.owner_id != current_user.id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Only the person who uploaded a document can move it"
        )
    if payload.deal_room_id:
        _require_room(payload.deal_room_id, current_user, session)
    repository.file_in_room(row, payload.deal_room_id or None)
    return DocumentSummary.from_report(
        report, deal_room_id=row.deal_room_id, uploaded_at=row.created_at
    )


__all__ = ["router"]
