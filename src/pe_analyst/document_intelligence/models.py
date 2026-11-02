"""Source-preserving contracts for PDF document intelligence."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from uuid import UUID, uuid4


class SectionKind(StrEnum):
    INCOME_STATEMENT = "income_statement"
    BALANCE_SHEET = "balance_sheet"
    CASH_FLOW_STATEMENT = "cash_flow_statement"
    MANAGEMENT_DISCUSSION = "management_discussion"
    NOTES_TO_FINANCIAL_STATEMENTS = "notes_to_financial_statements"
    RISK_FACTORS = "risk_factors"
    INDUSTRY = "industry"
    OTHER = "other"


@dataclass(slots=True, frozen=True)
class ExtractedTable:
    page_number: int
    rows: list[list[str | None]]


@dataclass(slots=True, frozen=True)
class ExtractedPage:
    page_number: int
    text: str
    tables: list[ExtractedTable] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ExtractedPDF:
    path: Path
    page_count: int
    pages: list[ExtractedPage]
    metadata: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class SourceReference:
    page_number: int
    excerpt: str
    confidence: float


@dataclass(slots=True, frozen=True)
class DocumentSection:
    kind: SectionKind
    title: str
    pages: list[int]
    references: list[SourceReference]


@dataclass(slots=True, frozen=True)
class StatementLineItem:
    statement: SectionKind
    label: str
    raw_values: list[str]
    source: SourceReference
    # Parallel to raw_values: the numeric value the service could parse out of each raw string,
    # or None where parsing failed (e.g. "n/a", a stray dash). Positional index-only mapping --
    # deliberately not auto-mapped to specific FinancialStatement fields (revenue, COGS, ...),
    # since that mapping is label-text-dependent and unreliable across companies.
    parsed_values: list[float | None] = field(default_factory=list)


@dataclass(slots=True, frozen=True)
class ExtractedRiskFactor:
    title: str
    text: str
    source: SourceReference


@dataclass(slots=True, frozen=True)
class ExtractedNote:
    title: str
    text: str
    source: SourceReference


@dataclass(slots=True)
class DocumentIntelligenceResult:
    document_id: UUID = field(default_factory=uuid4)
    source_path: Path = Path()
    file_name: str = ""
    page_count: int = 0
    sections: list[DocumentSection] = field(default_factory=list)
    statement_line_items: list[StatementLineItem] = field(default_factory=list)
    risk_factors: list[ExtractedRiskFactor] = field(default_factory=list)
    notes: list[ExtractedNote] = field(default_factory=list)
    management_discussion: list[SourceReference] = field(default_factory=list)
    industry_evidence: list[dict[str, object]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
