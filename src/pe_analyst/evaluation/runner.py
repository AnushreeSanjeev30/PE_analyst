"""Runs a system under test through a set of cases and aggregates a report."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .models import EvalCase, EvalReport, EvalResult


class EvaluationRunner:
    def __init__(
        self,
        system: Callable[[Any], Any],
        metric: Callable[[Any, Any], float],
        *,
        pass_threshold: float = 1.0,
    ) -> None:
        self.system = system
        self.metric = metric
        self.pass_threshold = pass_threshold

    def run(self, cases: list[EvalCase]) -> EvalReport:
        results = []
        for case in cases:
            prediction = None
            try:
                prediction = self.system(case.input)
                score = float(self.metric(prediction, case.expected))
                details = ""
            except Exception as error:  # noqa: BLE001 - a broken case must not abort the run
                score = 0.0
                details = f"{type(error).__name__}: {error}"
            results.append(
                EvalResult(
                    case_id=case.id,
                    score=score,
                    passed=score >= self.pass_threshold,
                    details=details,
                    prediction=prediction,
                    expected=case.expected,
                )
            )
        return EvalReport(results)


__all__ = ["EvaluationRunner"]
