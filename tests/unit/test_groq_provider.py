import json

import httpx
import pytest

from pe_analyst.core.config import Settings
from pe_analyst.llm import (
    GroqProvider,
    LLMConfigurationError,
    LLMMessage,
    LLMProviderError,
    LLMProviderName,
    LLMRequest,
    XAIProvider,
    build_llm_service,
    select_provider,
)


def _provider(handler: object) -> GroqProvider:
    provider = GroqProvider("test-key")
    provider.client = httpx.Client(
        base_url=GroqProvider.base_url,
        transport=httpx.MockTransport(handler),  # type: ignore[arg-type]
        headers={"Authorization": "Bearer test-key"},
    )
    return provider


def test_groq_provider_sends_openai_chat_payload_and_parses_reply() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-1",
                "choices": [{"message": {"role": "assistant", "content": '{"ok": true}'}}],
                "usage": {"prompt_tokens": 12, "completion_tokens": 4},
            },
        )

    response = _provider(handler).generate(
        LLMRequest(
            messages=[LLMMessage("user", "Summarise")],
            model="llama-3.3-70b-versatile",
            system_prompt="Be grounded",
            response_schema={"type": "object"},
        )
    )

    body = seen["body"]
    assert seen["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert seen["auth"] == "Bearer test-key"
    assert isinstance(body, dict)
    assert body["messages"][0] == {"role": "system", "content": "Be grounded"}
    assert body["response_format"] == {"type": "json_object"}
    assert response.text == '{"ok": true}'
    assert response.provider == LLMProviderName.GROQ
    assert (response.input_tokens, response.output_tokens) == (12, 4)


def test_groq_provider_surfaces_http_errors() -> None:
    provider = _provider(lambda request: httpx.Response(429, text="rate limited"))

    with pytest.raises(LLMProviderError, match="429"):
        provider.generate(LLMRequest(messages=[LLMMessage("user", "hi")], model="m"))


def test_openai_compatible_providers_require_keys() -> None:
    with pytest.raises(LLMConfigurationError, match="GROQ_API_KEY"):
        GroqProvider(None)
    with pytest.raises(LLMConfigurationError, match="XAI_API_KEY"):
        XAIProvider("")


def test_factory_enables_groq_and_xai_from_settings(test_settings: Settings) -> None:
    settings = test_settings.model_copy(update={"groq_api_key": "g", "xai_api_key": "x"})

    service = build_llm_service(settings)

    assert LLMProviderName.GROQ in service.providers
    assert LLMProviderName.XAI in service.providers


def test_select_provider_prefers_configured_then_falls_back(test_settings: Settings) -> None:
    groq = test_settings.model_copy(update={"groq_api_key": "g", "llm_model": "openai/gpt-oss-20b"})
    assert select_provider(groq, build_llm_service(groq)) == (
        LLMProviderName.GROQ,
        "openai/gpt-oss-20b",
    )

    openai_only = test_settings.model_copy(update={"openai_api_key": "o"})
    assert select_provider(openai_only, build_llm_service(openai_only)) == (
        LLMProviderName.OPENAI,
        openai_only.openai_model,
    )

    assert select_provider(test_settings, build_llm_service(test_settings)) is None
