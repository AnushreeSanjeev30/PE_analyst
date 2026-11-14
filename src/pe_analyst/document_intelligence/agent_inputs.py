"""Bridges a document-intelligence report into agent-workflow inputs.

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
"""

from __future__ import annotations

import re
from typing import Any

from .financial_mapping import MappedFinancials
from .schemas import DocumentIntelligenceReport

# Uploads are stored as "<uuid>_<original name>" so two files with the same name can't collide.
_STORAGE_PREFIX = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}_")


def display_name(file_name: str) -> str:
    """The name the user uploaded, without the storage prefix -- what a citation should show."""

    return _STORAGE_PREFIX.sub("", file_name)


def build_industry_inputs(
    report: DocumentIntelligenceReport,
    *,
    industry_name: str,
    competitors: list[dict[str, Any]] | None = None,
    market_growth_pct: float | None = None,
    competitive_position: str = "Neutral",
    porter_forces: dict[str, Any] | None = None,
    management_themes: list[str] | None = None,
) -> dict[str, Any]:
    """Build ``industry_inputs`` for ``IndustryAgent`` from an extracted document report."""

    return {
        "industry_name": industry_name,
        "evidence": [
            {**item.model_dump(), "source": display_name(item.source)}
            for item in report.industry_evidence
        ],
        "competitors": competitors or [],
        "market_growth_pct": market_growth_pct,
        "competitive_position": competitive_position,
        "porter_forces": porter_forces or {},
        "management_themes": management_themes or [],
    }


def build_due_diligence_inputs(report: DocumentIntelligenceReport) -> list[dict[str, Any]]:
    """Build ``due_diligence_inputs`` for ``DueDiligenceAgent`` from an extracted document report.

    Flattens the report's ``risk_factors`` and ``notes`` -- each already traced to a source page --
    into the item shape ``DueDiligenceTools`` expects. An empty result (no risk factors or notes
    were extracted) is valid: the agent treats it as "no diligence evidence supplied", not as a
    clean bill of health.
    """

    items = [
        {
            "title": factor.title,
            "text": factor.text,
            "source": display_name(report.file_name),
            "page_number": factor.source.page_number,
            "excerpt": factor.source.excerpt,
            "confidence": factor.source.confidence,
            "category": "risk_factor",
        }
        for factor in report.risk_factors
    ]
    items.extend(
        {
            "title": note.title,
            "text": note.text,
            "source": display_name(report.file_name),
            "page_number": note.source.page_number,
            "excerpt": note.source.excerpt,
            "confidence": note.source.confidence,
            "category": "note",
        }
        for note in report.notes
    )
    return items


def build_financial_evidence(
    report: DocumentIntelligenceReport, mapped: MappedFinancials
) -> list[dict[str, Any]]:
    """Trace each mapped financial-statement field back to the document line it came from.

    One entry per field that was read from the document: the page, the reported line label and
    the excerpt the extractor captured. Fields derived from several lines (EBITDA, total debt)
    cite the first contributing line and say so; they get a lower confidence because the figure
    is computed rather than quoted.
    """

    by_label = {item.label: item for item in report.statement_line_items}
    evidence: list[dict[str, Any]] = []
    for name, page_number in mapped.source_pages.items():
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
]
