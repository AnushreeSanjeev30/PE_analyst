from agents.base_agent import BaseAgent
from agents.orchestrator import DealAnalysisOrchestrator
from agents.orchestrator_models import RunStatus
from agents.state import AgentState
from agents.types import AgentResponse


class FakeAgent(BaseAgent):
    def __init__(self, name: str, fail: bool = False) -> None:
        super().__init__(name)
        self.fail = fail

    def execute(self, state: AgentState) -> AgentResponse:
        if self.fail:
            raise RuntimeError("deliberate failure")
        state.metadata.setdefault("execution_order", []).append(self.name)
        return AgentResponse(self.name, f"{self.name} completed", 0.9, [], {})


def test_orchestrator_runs_stages_in_order_and_records_trace() -> None:
    state = AgentState(company_name="ExampleCo", recommendation={"recommendation": "BUY"})
    orchestrator = DealAnalysisOrchestrator(
        [("financial", FakeAgent("Financial")), ("committee", FakeAgent("Committee"))]
    )

    result = orchestrator.run(state)

    assert result.status == RunStatus.COMPLETED
    assert result.final_recommendation == "BUY"
    assert [record.status for record in result.stages] == [RunStatus.COMPLETED, RunStatus.COMPLETED]
    assert state.metadata["execution_order"] == ["Financial", "Committee"]
    assert state.metadata["orchestration"] is result


def test_orchestrator_fails_fast_and_marks_remaining_stages_skipped() -> None:
    state = AgentState(company_name="ExampleCo")
    orchestrator = DealAnalysisOrchestrator(
        [
            ("financial", FakeAgent("Financial")),
            ("valuation", FakeAgent("Valuation", fail=True)),
            ("risk", FakeAgent("Risk")),
        ]
    )

    result = orchestrator.run(state)

    assert result.status == RunStatus.FAILED
    assert [record.status for record in result.stages] == [
        RunStatus.COMPLETED,
        RunStatus.FAILED,
        RunStatus.SKIPPED,
    ]
    assert "valuation" in result.error.lower()
