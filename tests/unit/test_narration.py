import json
from pathlib import Path

from tests.unit.test_deal_analysis import (
    _due_diligence_inputs,
    _financial_data,
    _industry_inputs,
    _valuation_inputs,
)

from agents import DealAnalysisInputs, Narrator, build_narrator, run_deal_analysis
from agents.narration import NarrationLog, find_ungrounded_numbers
from pe_analyst.core.config import Settings
from pe_analyst.llm import LLMProviderName, LLMRequest, LLMResponse, LLMService
from pe_analyst.llm.providers import LLMProvider


class ScriptedProvider(LLMProvider):
    name = LLMProviderName.GROQ

    def __init__(self, reply: str | Exception) -> None:
        self.reply = reply
        self.requests: list[LLMRequest] = []

    def generate(self, request: LLMRequest) -> LLMResponse:
        self.requests.append(request)
        if isinstance(self.reply, Exception):
            raise self.reply
        return LLMResponse(self.reply, self.name, request.model)


def _narrator(reply: str | Exception, log: NarrationLog | None = None) -> tuple[
    Narrator, ScriptedProvider
]:
    provider = ScriptedProvider(reply)
    service = LLMService({LLMProviderName.GROQ: provider})
    return Narrator(service, LLMProviderName.GROQ, "llama-test", log=log), provider


def test_narrator_parses_json_and_passes_facts_in_the_prompt() -> None:
    narrator, provider = _narrator(
        '{"commentary": "ROE of 25.0% is strong.", "key_points": ["Low leverage"]}'
    )

    narrative = narrator.narrate("Financial Agent", "Assess it.", {"ratios": {"roe": 0.25}})

    assert narrative.ok
    assert narrative.commentary == "ROE of 25.0% is strong."
    assert narrative.key_points == ["Low leverage"]
    assert narrative.ungrounded_numbers == []
    assert '"roe": 0.25' in provider.requests[0].messages[0].content


def test_narrator_flags_figures_that_are_not_in_the_facts() -> None:
    narrator, _ = _narrator('{"commentary": "IRR is 31.5% on a 9.5x exit.", "key_points": []}')

    narrative = narrator.narrate("Valuation Agent", "Explain.", {"irr": 0.229, "exit": 8.0})

    assert narrative.ungrounded_numbers == ["31.5%", "9.5x"]
    assert any("not present" in warning for warning in narrative.warnings)


def test_grounding_check_ignores_years_small_counts_and_rescaled_units() -> None:
    facts = {"revenue": 1_250_000_000.0, "margin": 0.22}

    assert find_ungrounded_numbers("In 2025 revenue was $1.25 billion at a 22% margin "
                                   "across 3 segments.", facts) == []


def test_narrator_never_raises_and_keeps_raw_text_when_not_json() -> None:
    failing, _ = _narrator(RuntimeError("quota exceeded"))
    plain, _ = _narrator("Just prose, no JSON.")

    failed = failing.narrate("Risk Agent", "Explain.", {})
    raw = plain.narrate("Risk Agent", "Explain.", {})

    assert not failed.ok
    assert "quota exceeded" in failed.warnings[0]
    assert raw.commentary == "Just prose, no JSON."
    assert raw.warnings


def test_narrator_logs_calls_in_chat_finetuning_format(tmp_path: Path) -> None:
    narrator, _ = _narrator('{"commentary": "Fine.", "key_points": []}', NarrationLog(tmp_path))

    narrator.narrate("Industry Agent", "Summarise.", {"growth": 0.12})

    lines = next(tmp_path.glob("narration_*.jsonl")).read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    assert [message["role"] for message in record["messages"]] == ["system", "user", "assistant"]
    assert record["agent"] == "Industry Agent"
    assert record["review"] is None


def test_build_narrator_is_none_without_credentials(test_settings: Settings) -> None:
    assert build_narrator(test_settings) is None
    configured = build_narrator(test_settings.model_copy(update={"groq_api_key": "key"}))
    assert configured is not None
    assert configured.model == test_settings.groq_model


def test_full_workflow_attaches_a_narrative_to_every_agent_and_a_memo_draft() -> None:
    narrator, provider = _narrator(
        '{"commentary": "## Executive Summary\\nGrounded.", "key_points": ["One"]}'
    )
    inputs = DealAnalysisInputs(
        company_name="ExampleCo",
        financial_data=_financial_data(),
        valuation_inputs=_valuation_inputs(),
        industry_inputs=_industry_inputs(),
        risk_inputs={"altman_z": 3.2, "piotroski_score": 7, "industry_risk_score": 30},
        due_diligence_inputs=_due_diligence_inputs(),
    )

    report = run_deal_analysis(inputs, narrator=narrator)

    assert report.is_complete
    assert "Investment Memo Agent" in report.narratives
    assert "Scenario Analysis Agent" in report.narratives
    assert report.investment_memo is not None
    assert report.investment_memo.llm_draft == "## Executive Summary\nGrounded."
    # Narration never changes the deterministic decision.
    assert report.final_recommendation == run_deal_analysis(inputs).final_recommendation
    assert len(provider.requests) == len(report.narratives)
