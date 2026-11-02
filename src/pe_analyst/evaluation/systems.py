"""Adapters that run each eval suite's input through the real pipeline.

Each ``*_system`` takes one case's ``input`` and returns a prediction shaped for that suite's
metric; :data:`SUITE_METRICS` pairs them. Agents run deterministically here (no narrator), so a
recommendation score measures the underwriting rules, not LLM variance.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agents import DealAnalysisInputs, run_deal_analysis
from pe_analyst.core.config import Settings
from pe_analyst.document_intelligence.financial_mapping import map_financial_statements
from pe_analyst.document_intelligence.schemas import DocumentIntelligenceReport
from pe_analyst.document_intelligence.service import DocumentIntelligenceService
from pe_analyst.engines.financial.models import FinancialStatement

from .metrics import citation_accuracy, extraction_field_accuracy, recommendation_agreement


def flatten_periods(values: dict[str, Any]) -> dict[str, Any]:
    """``{"current": {"revenue": 1}}`` -> ``{"current.revenue": 1}``; a flat dict means current."""

    if any(key in values for key in ("current", "previous")):
        return {
            f"{period}.{name}": value
            for period in ("current", "previous")
            for name, value in (values.get(period) or {}).items()
        }
    return {f"current.{name}": value for name, value in values.items()}


def extraction_system(pdf_path: str) -> dict[str, Any]:
    """Extracted values in currency units (document "in millions" etc. already applied).

    Ground truth from XBRL is in raw currency units, so predictions are scaled to match.
    """

    result = DocumentIntelligenceService().process(pdf_path)
    mapped = map_financial_statements(DocumentIntelligenceReport.from_result(result))
    scale = mapped.unit_multiplier
    return flatten_periods(
        {
            period: {name: value * scale for name, value in values.items()}
            for period, values in (("current", mapped.current), ("previous", mapped.previous))
        }
    )


def extraction_metric(predicted: dict[str, Any], expected: dict[str, Any]) -> float:
    return extraction_field_accuracy(predicted, flatten_periods(expected))


def build_citation_system(settings: Settings) -> Callable[[dict[str, Any]], list[dict[str, Any]]]:
    from pe_analyst.llm.factory import build_llm_service
    from pe_analyst.rag.answering import build_rag_service

    rag = build_rag_service(settings, build_llm_service(settings))
    ingested: set[str] = set()

    def system(case_input: dict[str, Any]) -> list[dict[str, Any]]:
        document_id = case_input.get("document_id")
        pdf = case_input.get("pdf")
        if pdf and document_id and document_id not in ingested:
            rag.retrieval.ingest_document(pdf, document_id)
            ingested.add(document_id)
        answer = rag.answer(case_input["question"], document_id=document_id)
        return [
            {"document_id": item.document_id, "page_number": item.page_number}
            for item in answer.citations
        ]

    return system


def deal_inputs_from_json(case_input: dict[str, Any]) -> DealAnalysisInputs:
    return DealAnalysisInputs(
        company_name=case_input["company_name"],
        financial_data={
            "current": FinancialStatement(**case_input["current_financials"]),
            "previous": FinancialStatement(**case_input["previous_financials"]),
        },
        valuation_inputs=case_input["valuation_inputs"],
        industry_inputs=case_input["industry_inputs"],
        risk_inputs=case_input.get("risk_inputs"),
        due_diligence_inputs=case_input.get("due_diligence_inputs"),
        scenario_inputs=case_input.get("scenario_inputs"),
    )


def recommendation_system(case_input: dict[str, Any]) -> str:
    report = run_deal_analysis(deal_inputs_from_json(case_input))
    if report.final_recommendation is None:
        raise RuntimeError(report.error or "Workflow produced no recommendation")
    return report.final_recommendation


def recommendation_metric(predicted: str, expected: str) -> float:
    return 1.0 if recommendation_agreement(predicted, expected) else 0.0


SUITE_METRICS: dict[str, Callable[[Any, Any], float]] = {
    "document_extraction": extraction_metric,
    "citation_accuracy": citation_accuracy,
    "recommendation_consistency": recommendation_metric,
}


def build_system(suite: str, settings: Settings) -> Callable[[Any], Any]:
    if suite == "document_extraction":
        return extraction_system
    if suite == "citation_accuracy":
        return build_citation_system(settings)
    if suite == "recommendation_consistency":
        return recommendation_system
    raise ValueError(f"Unknown suite {suite!r}")


__all__ = [
    "SUITE_METRICS",
    "build_system",
    "deal_inputs_from_json",
    "extraction_system",
    "flatten_periods",
    "recommendation_system",
]
