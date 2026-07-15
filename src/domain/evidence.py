"""
Evidence extracted from a source document.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import Field

from .common import ConfidenceScore, Entity


class Evidence(Entity):
    """
    Structured evidence supporting an AI-generated claim.
    """

    document_id: UUID

    claim: str

    page_number: int = Field(gt=0)

    confidence: ConfidenceScore

    excerpt: str | None = None

    reasoning: str | None = None