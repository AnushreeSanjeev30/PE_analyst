import pytest

from agents import AgentState, DueDiligenceAgent
from agents.due_diligence_models import DueDiligenceAssessment


def _item(title: str, text: str, **overrides: object) -> dict:
    base = {
        "title": title,
        "text": text,
        "source": "2025 Annual Report",
        "page_number": 14,
        "excerpt": text,
        "confidence": 0.85,
    }
    base.update(overrides)
    return base


def test_no_inputs_yields_an_incomplete_clear_assessment_with_low_confidence() -> None:
    state = AgentState(company_name="ExampleCo")

    report = DueDiligenceAgent().run(state).metadata["report"]

    assert report.summary.assessment == DueDiligenceAssessment.CLEAR
    assert report.summary.red_flag_count == 0
    assert report.summary.confidence == 0.40
    assert state.due_diligence["assessment"] == "Clear"


def test_benign_items_yield_a_clear_assessment_with_no_red_flags() -> None:
    state = AgentState(
        company_name="ExampleCo",
        metadata={
            "due_diligence_inputs": [
                _item("Hiring plans", "Management plans to expand the sales team."),
            ]
        },
    )

    report = DueDiligenceAgent().run(state).metadata["report"]

    assert report.summary.assessment == DueDiligenceAssessment.CLEAR
    assert report.red_flags == []
    assert report.items_reviewed == 1


def test_critical_keyword_drives_a_critical_assessment() -> None:
    state = AgentState(
        company_name="ExampleCo",
        metadata={
            "due_diligence_inputs": [
                _item(
                    "Auditor note",
                    "The auditor expressed going concern doubt about operations.",
                ),
                _item("Customer base", "Customer concentration remains elevated."),
            ]
        },
    )

    report = DueDiligenceAgent().run(state).metadata["report"]

    assert report.summary.assessment == DueDiligenceAssessment.CRITICAL
    assert report.summary.red_flag_count == 2
    assert {flag.severity.value for flag in report.red_flags} == {"Critical", "High"}


def test_malformed_input_raises() -> None:
    state = AgentState(
        company_name="ExampleCo",
        metadata={"due_diligence_inputs": [{"title": "Missing fields"}]},
    )

    with pytest.raises(ValueError, match="is missing"):
        DueDiligenceAgent().run(state)
