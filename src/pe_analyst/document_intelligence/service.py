"""Classifies PDF content and produces evidence-grounded analyst inputs."""

from __future__ import annotations

import re
from pathlib import Path

from .extractor import PDFExtractor
from .models import (
    DocumentIntelligenceResult,
    DocumentSection,
    ExtractedNote,
    ExtractedPDF,
    ExtractedRiskFactor,
    SectionKind,
    SourceReference,
    StatementLineItem,
)

_NOTE_HEADER = re.compile(r"Note\s+\d+[.:]", re.IGNORECASE)
_BLANK_VALUES = {"", "-", "—", "–", "n/a", "na", "nm"}
_CURRENCY_CELLS = {"$", "€", "£", "¥", "₹"}


def parse_numeric_value(raw: str) -> float | None:
    """Parse a raw statement cell into a float, or None if it isn't a number.

    Handles thousands separators, a leading currency symbol, a trailing percent sign, and
    parentheses as the accounting convention for a negative value -- e.g. ``"(1,234)"`` -> -1234.0.
    """

    text = raw.strip()
    if text.lower() in _BLANK_VALUES:
        return None
    negative = text.startswith("(") and text.endswith(")")
    if negative:
        text = text[1:-1]
    text = text.replace(",", "").replace("$", "").replace("%", "").strip()
    if not text:
        return None
    try:
        value = float(text)
    except ValueError:
        return None
    return -value if negative else value


def _label_end(values: list[str]) -> int:
    """Index of the first value cell; earlier cells are the row label.

    Whitespace-detected columns can split one label across cells ("Total" | "revenue").
    """

    for index, value in enumerate(values[1:], start=1):
        if parse_numeric_value(value) is not None:
            return index
    return 1


class DocumentIntelligenceService:
    section_markers = {
        SectionKind.INCOME_STATEMENT: (
            "statements of operations",
            "income statement",
            "statement of earnings",
        ),
        SectionKind.BALANCE_SHEET: ("balance sheets", "statement of financial position"),
        SectionKind.CASH_FLOW_STATEMENT: ("cash flows", "cash flow statement"),
        SectionKind.MANAGEMENT_DISCUSSION: (
            "management's discussion",
            "management discussion and analysis",
            "md&a",
        ),
        SectionKind.NOTES_TO_FINANCIAL_STATEMENTS: (
            "notes to financial statements",
            "notes to the financial statements",
            "notes to consolidated financial statements",
            "notes to the consolidated financial statements",
        ),
        SectionKind.RISK_FACTORS: ("risk factors",),
        SectionKind.INDUSTRY: ("market", "industry", "competition", "competitive"),
    }

    def __init__(self, extractor: PDFExtractor | None = None) -> None:
        self.extractor = extractor or PDFExtractor()

    def process(self, path: str | Path) -> DocumentIntelligenceResult:
        pdf = self.extractor.extract(Path(path))
        return self._interpret(pdf)

    def _interpret(self, pdf: ExtractedPDF) -> DocumentIntelligenceResult:
        sections = self._sections(pdf)
        line_items = self._statement_line_items(pdf, sections)
        risks = self._risk_factors(pdf, sections)
        notes = self._notes(pdf, sections)
        management = self._references_for_kind(pdf, sections, SectionKind.MANAGEMENT_DISCUSSION)
        industry = self._industry_evidence(pdf, sections)
        warnings: list[str] = []
        if not any(page.text.strip() for page in pdf.pages):
            warnings.append("No extractable text found; OCR is required for scanned PDFs.")
        if not line_items:
            warnings.append(
                "No structured financial statement rows were extracted; verify tables manually."
            )
        return DocumentIntelligenceResult(
            source_path=pdf.path,
            file_name=pdf.path.name,
            page_count=pdf.page_count,
            sections=sections,
            statement_line_items=line_items,
            risk_factors=risks,
            notes=notes,
            management_discussion=management,
            industry_evidence=industry,
            warnings=warnings,
        )

    def _sections(self, pdf: ExtractedPDF) -> list[DocumentSection]:
        sections: list[DocumentSection] = []
        for kind, markers in self.section_markers.items():
            matches = [
                page for page in pdf.pages if any(marker in page.text.lower() for marker in markers)
            ]
            if matches:
                sections.append(
                    DocumentSection(
                        kind,
                        kind.value.replace("_", " ").title(),
                        [page.page_number for page in matches],
                        [self._reference(page.text, page.page_number) for page in matches],
                    )
                )
        return sections

    def _statement_line_items(
        self, pdf: ExtractedPDF, sections: list[DocumentSection]
    ) -> list[StatementLineItem]:
        statement_pages = {
            page
            for section in sections
            if section.kind
            in {
                SectionKind.INCOME_STATEMENT,
                SectionKind.BALANCE_SHEET,
                SectionKind.CASH_FLOW_STATEMENT,
            }
            for page in section.pages
        }
        result: list[StatementLineItem] = []
        for page in pdf.pages:
            if page.page_number not in statement_pages:
                continue
            kind = next(
                section.kind
                for section in sections
                if page.page_number in section.pages
                and section.kind
                in {
                    SectionKind.INCOME_STATEMENT,
                    SectionKind.BALANCE_SHEET,
                    SectionKind.CASH_FLOW_STATEMENT,
                }
            )
            for table in page.tables:
                for row in table.rows:
                    values = [
                        value.strip()
                        for value in row
                        if value and value.strip() and value.strip() not in _CURRENCY_CELLS
                    ]
                    if len(values) < 2 or not any(re.search(r"\d", value) for value in values[1:]):
                        continue
                    split = _label_end(values)
                    result.append(
                        StatementLineItem(
                            kind,
                            " ".join(values[:split]),
                            values[split:],
                            self._reference(" | ".join(values), page.page_number),
                            [parse_numeric_value(value) for value in values[1:]],
                        )
                    )
        return result

    def _risk_factors(
        self, pdf: ExtractedPDF, sections: list[DocumentSection]
    ) -> list[ExtractedRiskFactor]:
        pages = {
            page
            for section in sections
            if section.kind == SectionKind.RISK_FACTORS
            for page in section.pages
        }
        factors: list[ExtractedRiskFactor] = []
        for page in pdf.pages:
            if page.page_number not in pages:
                continue
            for sentence in re.split(r"(?<=[.!?])\s+", page.text):
                if len(sentence) >= 40 and re.search(
                    r"\b(may|could|risk|adverse|uncertain)\b", sentence, re.IGNORECASE
                ):
                    text = sentence.strip()
                    factors.append(
                        ExtractedRiskFactor(
                            text[:80], text, self._reference(text, page.page_number)
                        )
                    )
        return factors

    def _notes(
        self, pdf: ExtractedPDF, sections: list[DocumentSection]
    ) -> list[ExtractedNote]:
        pages = {
            page
            for section in sections
            if section.kind == SectionKind.NOTES_TO_FINANCIAL_STATEMENTS
            for page in section.pages
        }
        notes: list[ExtractedNote] = []
        for page in pdf.pages:
            if page.page_number not in pages:
                continue
            headers = list(_NOTE_HEADER.finditer(page.text))
            for index, header in enumerate(headers):
                end = headers[index + 1].start() if index + 1 < len(headers) else len(page.text)
                title = re.sub(r"\s+", " ", header.group()).strip()
                body = page.text[header.end() : end].strip()
                if body:
                    source = self._reference(body, page.page_number)
                    notes.append(ExtractedNote(title, body, source))
        return notes

    def _references_for_kind(
        self, pdf: ExtractedPDF, sections: list[DocumentSection], kind: SectionKind
    ) -> list[SourceReference]:
        pages = {page for section in sections if section.kind == kind for page in section.pages}
        return [
            self._reference(page.text, page.page_number)
            for page in pdf.pages
            if page.page_number in pages
        ]

    def _industry_evidence(
        self, pdf: ExtractedPDF, sections: list[DocumentSection]
    ) -> list[dict[str, object]]:
        evidence: list[dict[str, object]] = []
        for page in pdf.pages:
            text = page.text.strip()
            lower = text.lower()
            for topic, terms in {
                "market": ("market", "industry", "demand"),
                "competition": ("competition", "competitor", "competitive"),
                "management": ("management", "strategy", "we expect"),
            }.items():
                if any(term in lower for term in terms):
                    reference = self._reference(text, page.page_number)
                    evidence.append(
                        {
                            "topic": topic,
                            "source": pdf.path.name,
                            "page_number": page.page_number,
                            "excerpt": reference.excerpt,
                            "claim": reference.excerpt,
                            "confidence": reference.confidence,
                        }
                    )
        return evidence

    @staticmethod
    def _reference(text: str, page_number: int) -> SourceReference:
        normalized = re.sub(r"\s+", " ", text).strip()
        return SourceReference(page_number, normalized[:500], 0.85 if normalized else 0.0)
