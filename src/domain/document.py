"""
Uploaded company document.
"""

from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from uuid import UUID

from pydantic import Field

from .common import Entity


class DocumentType(StrEnum):
    """
    Supported document categories.
    """

    ANNUAL_REPORT = "annual_report"
    QUARTERLY_REPORT = "quarterly_report"
    INVESTOR_PRESENTATION = "investor_presentation"
    CIM = "confidential_information_memorandum"
    PITCH_DECK = "pitch_deck"
    OTHER = "other"


class Document(Entity):
    """
    Represents one uploaded document.
    """

    company_id: UUID

    file_name: str

    file_path: Path

    document_type: DocumentType

    year: int = Field(
        ge=1900,
        le=2100,
    )

    page_count: int = Field(gt=0)

    language: str = "en"