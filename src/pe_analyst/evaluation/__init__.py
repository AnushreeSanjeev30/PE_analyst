"""Evaluation harness: metrics, JSON case loading, and a runner.

Cases live in ``datasets/<suite>/*.json`` (see ``datasets/README.md``). Run them with
``python scripts/run_evals.py``; the pipeline adapters are in :mod:`.systems` (imported lazily
because they pull in the whole agent stack).
"""

from __future__ import annotations

from .datasets import DATASETS_DIR, SPLITS, SUITES, load_cases
from .metrics import (
    citation_accuracy,
    extraction_field_accuracy,
    recommendation_agreement,
    values_match,
)
from .models import EvalCase, EvalReport, EvalResult
from .runner import EvaluationRunner

__all__ = [
    "DATASETS_DIR",
    "SPLITS",
    "SUITES",
    "load_cases",
    "values_match",
    "EvalCase",
    "EvalReport",
    "EvalResult",
    "EvaluationRunner",
    "citation_accuracy",
    "extraction_field_accuracy",
    "recommendation_agreement",
]
