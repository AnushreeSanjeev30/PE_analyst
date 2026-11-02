from pe_analyst.evaluation import (
    EvalCase,
    EvaluationRunner,
    citation_accuracy,
    extraction_field_accuracy,
    recommendation_agreement,
)


def test_citation_accuracy_scores_partial_overlap() -> None:
    predicted = [{"document_id": "doc-1", "page_number": 3}]
    expected = [
        {"document_id": "doc-1", "page_number": 3},
        {"document_id": "doc-1", "page_number": 9},
    ]

    assert citation_accuracy(predicted, expected) == 0.5


def test_citation_accuracy_is_perfect_when_nothing_is_expected_or_predicted() -> None:
    assert citation_accuracy([], []) == 1.0


def test_extraction_field_accuracy_scores_partial_matches() -> None:
    predicted = {"revenue": 1000.0, "net_income": 999.0}
    expected = {"revenue": 1000.0, "net_income": 100.0}

    assert extraction_field_accuracy(predicted, expected) == 0.5


def test_recommendation_agreement_is_case_insensitive() -> None:
    assert recommendation_agreement("buy", "BUY") is True
    assert recommendation_agreement("buy", "hold") is False


def test_evaluation_runner_aggregates_scores_and_pass_rate() -> None:
    cases = [
        EvalCase(id="a", input=2, expected=4),
        EvalCase(id="b", input=3, expected=999),
    ]
    runner = EvaluationRunner(
        system=lambda x: x * 2,
        metric=lambda predicted, expected: 1.0 if predicted == expected else 0.0,
    )

    report = runner.run(cases)

    assert report.pass_rate == 0.5
    assert report.mean_score == 0.5
    assert report.results[0].passed is True
    assert report.results[1].passed is False


def test_evaluation_runner_records_a_failure_instead_of_raising() -> None:
    def _broken_system(_: object) -> None:
        raise RuntimeError("boom")

    runner = EvaluationRunner(system=_broken_system, metric=lambda p, e: 1.0)

    report = runner.run([EvalCase(id="a", input=1, expected=1)])

    assert report.results[0].score == 0.0
    assert "boom" in report.results[0].details
