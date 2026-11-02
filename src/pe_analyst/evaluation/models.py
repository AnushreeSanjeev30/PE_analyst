"""Contracts for the evaluation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True, frozen=True)
class EvalCase:
    id: str
    input: Any
    expected: Any
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True, frozen=True)
class EvalResult:
    case_id: str
    score: float
    passed: bool
    details: str = ""
    # What the system produced, kept for error analysis.
    prediction: Any = None
    expected: Any = None


@dataclass(slots=True, frozen=True)
class EvalReport:
    results: list[EvalResult]

    @property
    def mean_score(self) -> float:
        if not self.results:
            return 0.0
        return sum(result.score for result in self.results) / len(self.results)

    @property
    def pass_rate(self) -> float:
        if not self.results:
            return 0.0
        return sum(1 for result in self.results if result.passed) / len(self.results)


__all__ = ["EvalCase", "EvalReport", "EvalResult"]
