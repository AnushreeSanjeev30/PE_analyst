"""Upload endpoint that turns a PDF (annual report, CIM, ...) into validated JSON."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from pe_analyst.core.config import Settings, get_settings
from pe_analyst.core.logging import get_logger

from .extractor import PDFExtractionError
from .schemas import DocumentIntelligenceReport
from .service import DocumentIntelligenceService

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
    return DocumentIntelligenceReport.from_result(result)


__all__ = ["router"]
