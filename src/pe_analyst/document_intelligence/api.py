"""Upload endpoint that turns a PDF (annual report, CIM, ...) into validated JSON."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from pe_analyst.auth.dependencies import get_current_user
from pe_analyst.auth.models import UserPublic
from pe_analyst.core.config import Settings, get_settings
from pe_analyst.core.logging import get_logger
from pe_analyst.db.session import get_db_session
from pe_analyst.rag.retrieval import build_retrieval_service

from .extractor import PDFExtractionError
from .repository import DocumentRepository, load_visible_report
from .schemas import DocumentIntelligenceReport, DocumentSummary
from .service import DocumentIntelligenceService
from .storage import DocumentReportStore

router = APIRouter(prefix="/documents", tags=["document-intelligence"])
logger = get_logger(__name__)


@router.post(
    "/upload",
    response_model=DocumentIntelligenceReport,
    status_code=status.HTTP_201_CREATED,
    summary="Upload an annual report, CIM, or other deal PDF for extraction",
)
async def upload_document(
    file: UploadFile,
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> DocumentIntelligenceReport:
    """Persist an uploaded PDF and return its validated document-intelligence report."""

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
    DocumentRepository(session).record(report, current_user.id)

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
    summary="List the caller's processed documents, most recently uploaded first",
)
async def list_documents(
    settings: Settings = Depends(get_settings),  # noqa: B008
    session: Session = Depends(get_db_session),  # noqa: B008
    current_user: UserPublic = Depends(get_current_user),  # noqa: B008
) -> list[DocumentSummary]:
    reports = (
        DocumentReportStore.load(document_id, settings)
        for document_id in DocumentRepository(session).visible_ids(current_user)
    )
    return [DocumentSummary.from_report(report) for report in reports if report is not None]


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


__all__ = ["router"]
