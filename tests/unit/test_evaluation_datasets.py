import json
from pathlib import Path

import pytest

from pe_analyst.evaluation import extraction_field_accuracy, load_cases, values_match
from pe_analyst.evaluation.systems import (
    extraction_metric,
    flatten_periods,
    recommendation_system,
)


def test_numeric_fields_match_within_tolerance() -> None:
    assert values_match(1_000_000.4, 1_000_000.0)
    assert values_match(1_004.0, 1_000.0)  # 0.4% -- rounding in a filing
    assert not values_match(1_010.0, 1_000.0)
    assert not values_match(True, 1)
    assert extraction_field_accuracy({"revenue": 1_000_000.4}, {"revenue": 1_000_000.0}) == 1.0


def test_extraction_metric_compares_both_periods() -> None:
    predicted = flatten_periods({"current": {"revenue": 100.0}, "previous": {"revenue": 90.0}})

    assert extraction_metric(predicted, {"current": {"revenue": 100.0},
                                         "previous": {"revenue": 50.0}}) == 0.5
    assert extraction_metric(predicted, {"revenue": 100.0}) == 1.0


def test_load_cases_filters_by_split_and_resolves_pdf_paths(tmp_path: Path) -> None:
    suite = tmp_path / "document_extraction"
    suite.mkdir()
    (suite / "samples").mkdir()
    (suite / "samples" / "a.pdf").write_bytes(b"%PDF")
    (suite / "a.json").write_text(
        json.dumps({"id": "a", "input": "samples/a.pdf", "expected": {"revenue": 1.0}})
    )
    (suite / "b.json").write_text(
        json.dumps({"id": "b", "split": "holdout", "input": "b.pdf", "expected": {}})
    )

    dev = load_cases("document_extraction", split="dev", root=tmp_path)

    assert [case.id for case in dev] == ["a"]
    assert Path(dev[0].input) == suite / "samples" / "a.pdf"
    assert len(load_cases("document_extraction", root=tmp_path)) == 2
    with pytest.raises(ValueError, match="Unknown suite"):
        load_cases("nope", root=tmp_path)


def test_shipped_recommendation_cases_run_through_the_real_workflow() -> None:
    cases = load_cases("recommendation_consistency")

    assert len(cases) >= 5
    predictions = {case.id: recommendation_system(case.input) for case in cases}
    assert set(predictions.values()) <= {"BUY", "HOLD", "REJECT"}
    # Unambiguous archetypes must never regress.
    assert predictions["distressed-overlevered"] == "REJECT"
    assert predictions["fraud-red-flag"] == "REJECT"
    assert predictions["quality-compounder-fair-price"] == "BUY"
