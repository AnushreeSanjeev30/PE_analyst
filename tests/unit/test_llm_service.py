import pytest

from pe_analyst.core.config import Settings
from pe_analyst.llm import (
    LLMConfigurationError,
    LLMMessage,
    LLMProviderName,
    LLMRequest,
    LLMResponse,
    LLMService,
    OpenAIProvider,
    build_llm_service,
)
from pe_analyst.llm.providers import LLMProvider


class FakeProvider(LLMProvider):
    name = LLMProviderName.OLLAMA

    def generate(self, request: LLMRequest) -> LLMResponse:
        return LLMResponse(
            "grounded response", self.name, request.model, input_tokens=3, output_tokens=2
        )


def test_llm_service_routes_to_configured_provider() -> None:
    request = LLMRequest(
        messages=[LLMMessage("user", "Summarize the report")], model="local-analyst"
    )

    result = LLMService({LLMProviderName.OLLAMA: FakeProvider()}).generate(
        LLMProviderName.OLLAMA, request
    )

    assert result.text == "grounded response"
    assert result.provider == LLMProviderName.OLLAMA


def test_llm_service_rejects_disabled_provider() -> None:
    service = LLMService({})
    request = LLMRequest(messages=[LLMMessage("user", "Hello")], model="gpt-5")

    with pytest.raises(ValueError, match="not enabled"):
        service.generate(LLMProviderName.OPENAI, request)


def test_openai_provider_requires_a_key() -> None:
    with pytest.raises(LLMConfigurationError, match="OPENAI_API_KEY"):
        OpenAIProvider(None)


def test_llm_service_factory_only_enables_configured_providers() -> None:
    service = build_llm_service(Settings(openai_api_key=None), include_ollama=False)

    assert service.providers == {}
