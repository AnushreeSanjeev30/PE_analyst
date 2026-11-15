"""Bridges document-intelligence reports into agent-workflow inputs.

``DealAnalysisInputs.industry_inputs`` (see ``agents.deal_analysis``) expects a dict shaped for
``IndustryTools.validate_and_normalize``: an ``industry_name`` plus source-grounded ``evidence``
entries carrying ``topic``/``source``/``page_number``/``excerpt``/``claim``/``confidence``. A
completed ``DocumentIntelligenceReport`` already extracted evidence in exactly that shape
(``industry_evidence``) -- ``build_industry_inputs`` just assembles the surrounding dict so upload
output can be handed straight to the agent workflow without hand-authoring evidence.

``DealAnalysisInputs.due_diligence_inputs`` expects a list shaped for
``DueDiligenceTools.validate_and_normalize``: source-grounded items carrying
``title``/``text``/``source``/``page_number``/``excerpt``/``confidence``. A completed
``DocumentIntelligenceReport`` already extracted candidate red-flag text in exactly that shape
across its ``risk_factors`` and ``notes`` -- ``build_due_diligence_inputs`` flattens both into that
list so the Due Diligence Agent can classify them without hand-authoring evidence either.

Every builder accepts one report or several. A deal usually arrives as a set of files (a CIM, the
audited accounts, a management presentation), and each piece of evidence keeps the
``document_id`` it came from so a citation can be opened in the right PDF.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .financial_mapping import STATEMENT_FIELDS, MappedFinancials, map_financial_statements
from .schemas import DocumentIntelligenceReport, display_name

Reports = DocumentIntelligenceReport | Sequence[DocumentIntelligenceReport]


def _as_list(reports: Reports) -> list[DocumentIntelligenceReport]:
    if isinstance(reports, DocumentIntelligenceReport):
        return [reports]
    return list(reports)


def build_industry_inputs(
    reports: Reports,
    *,
    industry_name: str,
    competitors: list[dict[str, Any]] | None = None,
    market_growth_pct: float | None = None,
    competitive_position: str = "Neutral",
    porter_forces: dict[str, Any] | None = None,
    management_themes: list[str] | None = None,
) -> dict[str, Any]:
    """Build ``industry_inputs`` for ``IndustryAgent`` from one or more extracted reports."""

    return {
        "industry_name": industry_name,
        "evidence": [
            {
                **item.model_dump(),
                "source": display_name(item.source),
                "document_id": report.document_id,
            }
            for report in _as_list(reports)
            for item in report.industry_evidence
        ],
        "competitors": competitors or [],
        "market_growth_pct": market_growth_pct,
        "competitive_position": competitive_position,
        "porter_forces": porter_forces or {},
        "management_themes": management_themes or [],
    }


def build_due_diligence_inputs(reports: Reports) -> list[dict[str, Any]]:
    """Build ``due_diligence_inputs`` for ``DueDiligenceAgent`` from one or more reports.

    Flattens each report's ``risk_factors`` and ``notes`` -- each already traced to a source
    page -- into the item shape ``DueDiligenceTools`` expects. An empty result (no risk factors
    or notes were extracted) is valid: the agent treats it as "no diligence evidence supplied",
    not as a clean bill of health.
    """

    items: list[dict[str, Any]] = []
    for report in _as_list(reports):
        source = display_name(report.file_name)
        for category, entries in (("risk_factor", report.risk_factors), ("note", report.notes)):
            items.extend(
                {
                    "title": entry.title,
                    "text": entry.text,
                    "source": source,
                    "document_id": report.document_id,
                    "page_number": entry.source.page_number,
                    "excerpt": entry.source.excerpt,
                    "confidence": entry.source.confidence,
                    "category": category,
                }
                for entry in entries
            )
    return items


def map_financials_across(
    reports: Reports,
) -> tuple[MappedFinancials, dict[str, DocumentIntelligenceReport]]:
    """Map the financial statements from a set of documents, taking each field from the first
    document that actually reports it.

    Returns the merged mapping and, per field, the report it was read from. Order matters:
    list the most authoritative document (the audited accounts) first.

    Two details keep the merge honest:

    * A field a document only *defaulted* (inventory assumed zero when no line was found) never
      beats a value another document really reports.
    * Documents may present figures in different units ("in thousands" vs "in millions"). Values
      are converted into the units of the first document that contributes a figure, and a
      warning records that a conversion happened.
    """

    merged = MappedFinancials()
    sources: dict[str, DocumentIntelligenceReport] = {}
    base_multiplier: float | None = None
    defaults: list[tuple[MappedFinancials, float]] = []

    for report in _as_list(reports):
        mapped = map_financial_statements(report)
        defaults.append((mapped, mapped.unit_multiplier))
        for name in STATEMENT_FIELDS:
            reported = name in mapped.source_pages
            complete = name in mapped.current and name in mapped.previous
            if not reported or not complete or name in sources:
                continue
            if base_multiplier is None:
                base_multiplier = mapped.unit_multiplier
                merged.unit_multiplier = base_multiplier
            scale = mapped.unit_multiplier / base_multiplier
            if scale != 1.0:
                note = (
                    f"{display_name(report.file_name)} reports in different units; its figures "
                    "were converted to match the first document."
                )
                if note not in merged.warnings:
                    merged.warnings.append(note)
            merged.current[name] = mapped.current[name] * scale
            merged.previous[name] = mapped.previous[name] * scale
            merged.source_pages[name] = mapped.source_pages[name]
            merged.source_labels[name] = mapped.source_labels[name]
            sources[name] = report
        for warning in mapped.warnings:
            # Derivation notes only matter for the document a derived field was taken from.
            derived = warning.split(" ", 1)[0]
            if sources.get(derived) is report and warning not in merged.warnings:
                merged.warnings.append(warning)

    # Fall back to defaulted values (inventory = 0) only where no document reported the field.
    for mapped, _ in defaults:
        for name in STATEMENT_FIELDS:
            if name not in merged.current and name in mapped.current and name in mapped.previous:
                merged.current[name] = mapped.current[name]
                merged.previous[name] = mapped.previous[name]
                for warning in mapped.warnings:
                    if name in warning.lower() and warning not in merged.warnings:
                        merged.warnings.append(warning)

    merged.missing = [
        name
        for name in STATEMENT_FIELDS
        if name not in merged.current or name not in merged.previous
    ]
    return merged, sources


def build_financial_evidence(
    mapped: MappedFinancials, sources: dict[str, DocumentIntelligenceReport]
) -> list[dict[str, Any]]:
    """Trace each mapped financial-statement field back to the document line it came from.

    One entry per field that was read from a document: the file, the page, the reported line
    label and the excerpt the extractor captured. Fields derived from several lines (EBITDA,
    total debt) cite the first contributing line and say so; they get a lower confidence
    because the figure is computed rather than quoted.
    """

    evidence: list[dict[str, Any]] = []
    for name, page_number in mapped.source_pages.items():
        report = sources.get(name)
        if report is None:
            continue
        by_label = {item.label: item for item in report.statement_line_items}
        label = mapped.source_labels.get(name, name)
        item = by_label.get(label)
        current = mapped.current.get(name)
        value = "" if current is None else f" = {current:,.2f}"
        if item is not None:
            excerpt = item.source.excerpt or f"{label}{value}"
            confidence = item.source.confidence
        else:
            excerpt = f"Derived from reported lines: {label}{value}"
            confidence = 0.5
        evidence.append(
            {
                "field": name,
                "source": display_name(report.file_name),
                "document_id": report.document_id,
                "page_number": page_number,
                "excerpt": f'{name.replace("_", " ")} read from "{label}"{value}. {excerpt}',
                "confidence": confidence,
            }
        )
    return evidence


__all__ = [
    "build_due_diligence_inputs",
    "build_financial_evidence",
    "build_industry_inputs",
    "display_name",
    "map_financials_across",
]
