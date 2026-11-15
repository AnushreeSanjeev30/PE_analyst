"""Compares two saved analyses: what the analyst changed, and what that did to the answer.

Deal work is iterative. The team re-runs a deal with a lower entry price, a harsher downside or
a newly received document, and the question is always the same: what moved, and why? This
module lines up two saved runs and reports

* the recommendation before and after,
* the headline results (returns, value per share, risk, diligence),
* each scorecard area whose vote flipped, and
* every input that differs between the two requests,

so the change in outcome can be read against the change in assumptions. It is pure: it works on
the stored request and report JSON and runs nothing.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel

_MAX_INPUT_CHANGES = 200
_MAX_VALUE_CHARS = 160


class RunRef(BaseModel):
    id: str
    company_name: str
    status: str
    recommendation: str | None
    created_at: Any


class MetricChange(BaseModel):
    key: str
    label: str
    # "percent" | "multiple" | "number" | "money" | "text"
    unit: str
    base: float | str | None
    other: float | str | None
    # other - base, for numeric metrics present in both runs.
    delta: float | None = None
    changed: bool


class DriverChange(BaseModel):
    area: str
    base_direction: str | None
    other_direction: str | None
    base_statement: str | None
    other_statement: str | None
    changed: bool


class InputChange(BaseModel):
    # Dotted path into the request, e.g. "valuation_assumptions.entry_multiple".
    path: str
    base: Any
    other: Any


class AnalysisComparison(BaseModel):
    base: RunRef
    other: RunRef
    recommendation_changed: bool
    # One plain sentence stating the headline outcome of the comparison.
    summary: str
    metrics: list[MetricChange]
    drivers: list[DriverChange]
    input_changes: list[InputChange]
    # True when more inputs differ than are listed.
    input_changes_truncated: bool = False


def _dig(data: Any, *path: str) -> Any:
    for key in path:
        if not isinstance(data, dict):
            return None
        data = data.get(key)
    return data


_Metric = tuple[str, str, str, Callable[[dict[str, Any]], Any]]

_METRICS: tuple[_Metric, ...] = (
    ("irr", "Base-case IRR", "percent",
     lambda r: _dig(r, "valuation_report", "lbo_returns", "irr")),
    ("moic", "Base-case MOIC", "multiple",
     lambda r: _dig(r, "valuation_report", "lbo_returns", "moic")),
    ("entry_ev", "Entry enterprise value", "money",
     lambda r: _dig(r, "valuation_report", "lbo_returns", "entry_enterprise_value")),
    ("fair_value", "Fair value per share", "money",
     lambda r: _dig(r, "valuation_report", "summary", "fair_value_per_share")),
    ("upside", "Upside / downside to fair value", "percent",
     lambda r: _dig(r, "valuation_report", "summary", "upside_downside_pct")),
    ("weighted_irr", "Probability-weighted IRR", "percent",
     lambda r: _dig(r, "scenario_report", "summary", "probability_weighted_irr")),
    ("target_probability", "Chance of hitting target IRR", "percent",
     lambda r: _dig(r, "scenario_report", "probability_of_meeting_target")),
    ("breakeven_exit", "Break-even exit multiple", "multiple",
     lambda r: _dig(r, "scenario_report", "breakeven_exit_multiple")),
    ("support_weight", "Scorecard weight in support", "percent",
     lambda r: _dig(r, "ic_decision", "explanation", "support_weight")),
    ("risk_score", "Risk score (0-100)", "number",
     lambda r: _dig(r, "risk_report", "summary", "score")),
    ("risk_level", "Risk level", "text",
     lambda r: _dig(r, "risk_report", "summary", "level")),
    ("financial_health", "Financial health", "text",
     lambda r: _dig(r, "financial_report", "summary", "health")),
    ("competitive_position", "Competitive position", "text",
     lambda r: _dig(r, "industry_report", "summary", "competitive_position")),
    ("dd_assessment", "Due diligence assessment", "text",
     lambda r: _dig(r, "due_diligence_report", "summary", "assessment")),
    ("red_flags", "Red flags", "number",
     lambda r: _dig(r, "due_diligence_report", "summary", "red_flag_count")),
    ("risk_officer", "Risk Officer verdict", "text",
     lambda r: _dig(r, "ic_decision", "risk_officer", "verdict")),
)


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _differs(base: Any, other: Any) -> bool:
    if _is_number(base) and _is_number(other):
        scale = max(abs(base), abs(other), 1e-12)
        return bool(abs(base - other) / scale > 1e-9)
    return bool(base != other)


def _metric_changes(base: dict[str, Any], other: dict[str, Any]) -> list[MetricChange]:
    changes = []
    for key, label, unit, read in _METRICS:
        left, right = read(base), read(other)
        if left is None and right is None:
            continue
        numeric = _is_number(left) and _is_number(right)
        changes.append(
            MetricChange(
                key=key,
                label=label,
                unit=unit,
                base=left,
                other=right,
                delta=(right - left) if numeric else None,
                changed=_differs(left, right),
            )
        )
    return changes


def _driver_changes(base: dict[str, Any], other: dict[str, Any]) -> list[DriverChange]:
    def by_area(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
        drivers = _dig(report, "ic_decision", "explanation", "drivers") or []
        return {str(driver.get("area")): driver for driver in drivers}

    left, right = by_area(base), by_area(other)
    changes = []
    for area in list(left) + [area for area in right if area not in left]:
        before, after = left.get(area), right.get(area)
        before_direction = before.get("direction") if before else None
        after_direction = after.get("direction") if after else None
        changes.append(
            DriverChange(
                area=area,
                base_direction=before_direction,
                other_direction=after_direction,
                base_statement=before.get("statement") if before else None,
                other_statement=after.get("statement") if after else None,
                changed=before_direction != after_direction,
            )
        )
    # Flipped votes first: they are what explains a changed recommendation.
    changes.sort(key=lambda change: not change.changed)
    return changes


def _shorten(value: Any) -> Any:
    if isinstance(value, dict | list):
        text = str(value)
        return text if len(text) <= _MAX_VALUE_CHARS else text[: _MAX_VALUE_CHARS - 3] + "..."
    if isinstance(value, str) and len(value) > _MAX_VALUE_CHARS:
        return value[: _MAX_VALUE_CHARS - 3] + "..."
    return value


def diff_inputs(base: Any, other: Any, path: str = "") -> list[InputChange]:
    """Every leaf that differs between two request payloads, as dotted paths.

    Lists are compared position by position (the operating projection is a list of years),
    and a value present on only one side is reported against ``None``.
    """

    if isinstance(base, dict) and isinstance(other, dict):
        changes: list[InputChange] = []
        for key in list(base) + [key for key in other if key not in base]:
            child = f"{path}.{key}" if path else str(key)
            changes += diff_inputs(base.get(key), other.get(key), child)
        return changes
    if isinstance(base, list) and isinstance(other, list):
        changes = []
        for index in range(max(len(base), len(other))):
            left = base[index] if index < len(base) else None
            right = other[index] if index < len(other) else None
            changes += diff_inputs(left, right, f"{path}[{index}]")
        return changes
    if _differs(base, other):
        return [InputChange(path=path, base=_shorten(base), other=_shorten(other))]
    return []


def _summary(
    base: RunRef, other: RunRef, drivers: list[DriverChange], input_count: int
) -> str:
    flipped = [driver.area for driver in drivers if driver.changed]
    inputs = (
        "No inputs differ between the two runs."
        if input_count == 0
        else f"{input_count} input{'s differ' if input_count != 1 else ' differs'}."
    )
    if base.recommendation != other.recommendation:
        outcome = (
            f"The recommendation changed from {base.recommendation or 'none'} to "
            f"{other.recommendation or 'none'}."
        )
    else:
        outcome = f"The recommendation is {other.recommendation or 'none'} in both runs."
    votes = (
        f" Scorecard areas that flipped: {', '.join(flipped)}."
        if flipped
        else " No scorecard area changed its vote."
    )
    return f"{outcome}{votes} {inputs}"


def compare_analyses(base: Any, other: Any) -> AnalysisComparison:
    """Compare two saved analyses (``DealAnalysisModel`` rows, or anything shaped like one)."""

    def ref(row: Any) -> RunRef:
        return RunRef(
            id=row.id,
            company_name=row.company_name,
            status=row.status,
            recommendation=row.recommendation,
            created_at=row.created_at,
        )

    base_ref, other_ref = ref(base), ref(other)
    base_report, other_report = base.report or {}, other.report or {}
    drivers = _driver_changes(base_report, other_report)
    inputs = diff_inputs(base.request or {}, other.request or {})
    return AnalysisComparison(
        base=base_ref,
        other=other_ref,
        recommendation_changed=base_ref.recommendation != other_ref.recommendation,
        summary=_summary(base_ref, other_ref, drivers, len(inputs)),
        metrics=_metric_changes(base_report, other_report),
        drivers=drivers,
        input_changes=inputs[:_MAX_INPUT_CHANGES],
        input_changes_truncated=len(inputs) > _MAX_INPUT_CHANGES,
    )


__all__ = [
    "AnalysisComparison",
    "DriverChange",
    "InputChange",
    "MetricChange",
    "RunRef",
    "compare_analyses",
    "diff_inputs",
]
