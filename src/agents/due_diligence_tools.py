"""Deterministic, keyword-based red-flag classification for the Due Diligence Agent.

Severity is assigned by matching source-grounded diligence items (extracted risk
factors and notes -- see ``pe_analyst.document_intelligence.agent_inputs``) against
fixed PE red-flag vocabularies. This mirrors the rest of the underwriting stack's
control principle: evidence extraction only cites text, the agent only interprets --
severity is never inferred by an LLM.
"""

from __future__ import annotations

from typing import Any

from .due_diligence_models import RedFlag, RedFlagSeverity
from .industry_models import SourceCitation


class DueDiligenceTools:
    required_fields = {"title", "text", "source", "page_number", "excerpt", "confidence"}

    _CRITICAL_TERMS = (
        "going concern",
        "material weakness",
        "restatement",
        "fraud",
        "investigation",
        "default",
        "covenant breach",
        "bankruptcy",
        "sec inquiry",
        "accounting irregularit",
    )
    _HIGH_TERMS = (
        "litigation",
        "lawsuit",
        "regulatory action",
        "key person",
        "customer concentration",
        "related party",
        "impairment",
        "data breach",
        "non-compliance",
    )
    _MODERATE_TERMS = (
        "competition",
        "regulatory",
        "supply chain",
        "turnover",
        "seasonality",
        "customer churn",
        "pending claim",
    )

    def validate_and_normalize(self, raw: Any) -> list[dict[str, Any]]:
        if raw is None:
            return []
        if not isinstance(raw, list):
            raise ValueError("due_diligence_inputs must be a list of source-grounded items")
        for item in raw:
            missing = self.required_fields - item.keys()
            if missing:
                raise ValueError(f"Due diligence item is missing: {', '.join(sorted(missing))}")
            if int(item["page_number"]) < 1 or not 0 <= float(item["confidence"]) <= 1:
                raise ValueError("Due diligence item page_number/confidence is invalid")
        return raw

    def classify(self, text: str) -> RedFlagSeverity:
        lowered = text.lower()
        if any(term in lowered for term in self._CRITICAL_TERMS):
            return RedFlagSeverity.CRITICAL
        if any(term in lowered for term in self._HIGH_TERMS):
            return RedFlagSeverity.HIGH
        if any(term in lowered for term in self._MODERATE_TERMS):
            return RedFlagSeverity.MODERATE
        return RedFlagSeverity.LOW

    def evaluate(self, items: list[dict[str, Any]]) -> list[RedFlag]:
        flags = []
        for item in items:
            severity = self.classify(f"{item['title']} {item['text']}")
            if severity == RedFlagSeverity.LOW:
                continue
            flags.append(
                RedFlag(
                    title=item["title"],
                    category=item.get("category", "diligence"),
                    severity=severity,
                    rationale=item["text"],
                    citation=SourceCitation(
                        item["source"],
                        int(item["page_number"]),
                        item["excerpt"],
                        float(item["confidence"]),
                    ),
                )
            )
        return flags
