"""Pydantic contracts that turn document-intelligence output into validated JSON.

``DocumentIntelligenceService.process`` returns plain dataclasses (fast to
build, easy to unit test). Those aren't directly JSON-safe -- ``Path`` and
``UUID`` fields, ``StrEnum`` members that need normalizing to plain strings --
and nothing stops a bad extraction from serializing malformed data (a page
number of zero, a confidence above 1.0). ``DocumentIntelligenceReport`` is the
validated boundary between the extraction pipeline and any consumer (API
response, stored artifact, downstream agent input) that needs guaranteed-valid
JSON with every claim traceable to a page.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .models import DocumentIntelligenceResult, SectionKind


class SourceReferenceSchema(BaseModel):
    """A claim traced back to the exact page it came from."""

    model_config = ConfigDict(frozen=True)

    page_number: int = Field(ge=1)
    excerpt: str
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentSectionSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: SectionKind
    title: str
    pages: list[int]
    references: list[SourceReferenceSchema]


class StatementLineItemSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    statement: SectionKind
    label: str
    raw_values: list[str]
    source: SourceReferenceSchema


class ExtractedRiskFactorSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    text: str
    source: SourceReferenceSchema


class ExtractedNoteSchema(BaseModel):
    model_config = ConfigDict(frozen=True)

    title: str
    text: str
    source: SourceReferenceSchema


class IndustryEvidenceSchema(BaseModel):
    """Shaped to feed ``IndustryAgent`` inputs directly (see agents.deal_analysis)."""

    model_config = ConfigDict(frozen=True)

    topic: str
    source: str
    page_number: int = Field(ge=1)
    excerpt: str
    claim: str
    confidence: float = Field(ge=0.0, le=1.0)


class DocumentIntelligenceReport(BaseModel):
    """Validated, JSON-serializable view of a completed document-intelligence run."""

    model_config = ConfigDict(frozen=True)

    document_id: str
    file_name: str
    page_count: int = Field(ge=0)
    sections: list[DocumentSectionSchema]
    statement_line_items: list[StatementLineItemSchema]
    risk_factors: list[ExtractedRiskFactorSchema]
    notes: list[ExtractedNoteSchema]
    management_discussion: list[SourceReferenceSchema]
    industry_evidence: list[IndustryEvidenceSchema]
    warnings: list[str]

    @classmethod
    def from_result(cls, result: DocumentIntelligenceResult) -> DocumentIntelligenceReport:
        """Validate a raw extraction result into guaranteed-valid JSON."""

        return cls(
            document_id=str(result.document_id),
            file_name=result.file_name,
            page_count=result.page_count,
            sections=[
                DocumentSectionSchema(
                    kind=section.kind,
                    title=section.title,
                    pages=section.pages,
                    references=[
                        SourceReferenceSchema(
                            page_number=ref.page_number,
                            excerpt=ref.excerpt,
                            confidence=ref.confidence,
                        )
                        for ref in section.references
                    ],
                )
                for section in result.sections
            ],
            statement_line_items=[
                StatementLineItemSchema(
                    statement=item.statement,
                    label=item.label,
                    raw_values=item.raw_values,
                    source=SourceReferenceSchema(
                        page_number=item.source.page_number,
                        excerpt=item.source.excerpt,
                        confidence=item.source.confidence,
                    ),
                )
                for item in result.statement_line_items
            ],
            risk_factors=[
                ExtractedRiskFactorSchema(
                    title=factor.title,
                    text=factor.text,
                    source=SourceReferenceSchema(
                        page_number=factor.source.page_number,
                        excerpt=factor.source.excerpt,
                        confidence=factor.source.confidence,
                    ),
                )
                for factor in result.risk_factors
            ],
            notes=[
                ExtractedNoteSchema(
                    title=note.title,
                    text=note.text,
                    source=SourceReferenceSchema(
                        page_number=note.source.page_number,
                        excerpt=note.source.excerpt,
                        confidence=note.source.confidence,
                    ),
                )
                for note in result.notes
            ],
            management_discussion=[
                SourceReferenceSchema(
                    page_number=ref.page_number, excerpt=ref.excerpt, confidence=ref.confidence
                )
                for ref in result.management_discussion
            ],
            industry_evidence=[
                IndustryEvidenceSchema(**item) for item in result.industry_evidence
            ],
            warnings=result.warnings,
        )


__all__ = [
    "DocumentIntelligenceReport",
    "DocumentSectionSchema",
    "ExtractedNoteSchema",
    "ExtractedRiskFactorSchema",
    "IndustryEvidenceSchema",
    "SectionKind",
    "SourceReferenceSchema",
    "StatementLineItemSchema",
]
