"""Reusable scoring functions for the harness's three named use cases."""

from __future__ import annotations

import math
from typing import Any


def citation_accuracy(
    predicted: list[dict[str, Any]], expected: list[dict[str, Any]]
) -> float:
    """Fraction of ``expected`` citations found in ``predicted``, matched by document+page."""

    if not expected:
        return 1.0 if not predicted else 0.0
    predicted_keys = {(item.get("document_id"), item.get("page_number")) for item in predicted}
    matched = sum(
        1
        for item in expected
        if (item.get("document_id"), item.get("page_number")) in predicted_keys
    )
    return matched / len(expected)


def values_match(
    predicted: Any, expected: Any, *, rel_tol: float = 0.005, abs_tol: float = 0.5
) -> bool:
    """Numbers match within tolerance (default 0.5% or 0.5 units); anything else exactly.

    Filings round to thousands or millions, so exact float equality fails for correct
    extractions -- ``1_000_000.0`` vs ``1_000_000.4`` is the same reported figure.
    """

    numeric = (int, float)
    if isinstance(predicted, bool) != isinstance(expected, bool):
        return False  # True == 1 in Python; a flag is not a figure
    if (
        isinstance(predicted, numeric)
        and isinstance(expected, numeric)
        and not isinstance(predicted, bool)
        and not isinstance(expected, bool)
    ):
        return math.isclose(float(predicted), float(expected), rel_tol=rel_tol, abs_tol=abs_tol)
    return bool(predicted == expected)


def extraction_field_accuracy(
    predicted: dict[str, Any],
    expected: dict[str, Any],
    *,
    rel_tol: float = 0.005,
    abs_tol: float = 0.5,
) -> float:
    """Fraction of ``expected`` fields that ``predicted`` reproduces (numbers within tolerance)."""

    if not expected:
        return 1.0 if not predicted else 0.0
    matched = sum(
        1
        for key, value in expected.items()
        if key in predicted
        and values_match(predicted[key], value, rel_tol=rel_tol, abs_tol=abs_tol)
    )
    return matched / len(expected)


def recommendation_agreement(predicted: str, expected: str) -> bool:
    """Case-insensitive exact match, e.g. comparing BUY/HOLD/REJECT recommendations."""

    return predicted.strip().casefold() == expected.strip().casefold()


__all__ = [
    "citation_accuracy",
    "extraction_field_accuracy",
    "recommendation_agreement",
    "values_match",
]
