"""Validation and evidence-preserving utilities for the Industry Agent."""

from __future__ import annotations

from typing import Any

from .industry_models import CompetitorProfile, SourceCitation


class IndustryTools:
    required_topics = {"market", "competition", "management"}

    def validate_and_normalize(self, raw: Any) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ValueError("state.metadata['industry_inputs'] must be a dictionary")
        missing = {"industry_name", "evidence"} - raw.keys()
        if missing:
            raise ValueError(f"industry_inputs is missing: {', '.join(sorted(missing))}")
        evidence = raw["evidence"]
        if not isinstance(evidence, list) or not evidence:
            raise ValueError("industry_inputs.evidence must contain source-grounded evidence")
        for item in evidence:
            required = {"topic", "source", "page_number", "excerpt", "claim", "confidence"}
            missing_fields = required - item.keys()
            if missing_fields:
                raise ValueError(f"Evidence is missing: {', '.join(sorted(missing_fields))}")
            if item["topic"] not in self.required_topics:
                raise ValueError("Evidence topic must be market, competition, or management")
            if int(item["page_number"]) < 1 or not 0 <= float(item["confidence"]) <= 1:
                raise ValueError("Evidence page_number/confidence is invalid")
        return raw

    @staticmethod
    def citations(evidence: list[dict[str, Any]], topic: str) -> list[SourceCitation]:
        return [
            SourceCitation(
                item["source"], int(item["page_number"]), item["excerpt"], float(item["confidence"])
            )
            for item in evidence
            if item["topic"] == topic
        ]

    @staticmethod
    def competitors(raw: list[dict[str, Any]]) -> list[CompetitorProfile]:
        return [CompetitorProfile(**item) for item in raw]
