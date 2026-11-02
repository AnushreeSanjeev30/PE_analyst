"""Settings-based construction for the enabled LLM provider registry."""

from __future__ import annotations

from pe_analyst.core.config import Settings

from .models import LLMProviderName
from .providers import (
    AnthropicProvider,
    GeminiProvider,
    GroqProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
    XAIProvider,
)
from .service import LLMService


def build_llm_service(settings: Settings, *, include_ollama: bool = False) -> LLMService:
    """Build only providers whose credentials are present in application settings."""
    providers: dict[LLMProviderName, LLMProvider] = {}
    if settings.openai_api_key:
        providers[LLMProviderName.OPENAI] = OpenAIProvider(
            settings.openai_api_key, settings.llm_timeout_seconds
        )
    if settings.anthropic_api_key:
        providers[LLMProviderName.ANTHROPIC] = AnthropicProvider(
            settings.anthropic_api_key, settings.llm_timeout_seconds
        )
    if settings.gemini_api_key:
        providers[LLMProviderName.GEMINI] = GeminiProvider(
            settings.gemini_api_key, settings.llm_timeout_seconds
        )
    if settings.groq_api_key:
        providers[LLMProviderName.GROQ] = GroqProvider(
            settings.groq_api_key, settings.llm_timeout_seconds
        )
    if settings.xai_api_key:
        providers[LLMProviderName.XAI] = XAIProvider(
            settings.xai_api_key, settings.llm_timeout_seconds
        )
    if include_ollama or settings.llm_provider == LLMProviderName.OLLAMA.value:
        providers[LLMProviderName.OLLAMA] = OllamaProvider(
            settings.ollama_base_url, settings.llm_timeout_seconds
        )
    return LLMService(providers)


def _default_model(settings: Settings, provider: LLMProviderName) -> str:
    return {
        LLMProviderName.GROQ: settings.groq_model,
        LLMProviderName.XAI: settings.xai_model,
        LLMProviderName.OPENAI: settings.openai_model,
        LLMProviderName.ANTHROPIC: "claude-haiku-5-5",
        LLMProviderName.GEMINI: "gemini-2.5-flash",
        LLMProviderName.OLLAMA: settings.ollama_model,
    }[provider]


_FALLBACK_ORDER = (
    LLMProviderName.GROQ,
    LLMProviderName.OPENAI,
    LLMProviderName.ANTHROPIC,
    LLMProviderName.GEMINI,
    LLMProviderName.XAI,
)


def select_provider(
    settings: Settings, service: LLMService
) -> tuple[LLMProviderName, str] | None:
    """``LLM_PROVIDER`` and its model; else the first credentialed provider; else None.

    ``LLM_MODEL`` only applies to the configured provider -- a fallback uses its own default.
    """

    try:
        preferred: LLMProviderName | None = LLMProviderName(settings.llm_provider.lower())
    except ValueError:
        preferred = None
    if preferred is not None and preferred in service.providers:
        return preferred, settings.llm_model or _default_model(settings, preferred)
    for provider in _FALLBACK_ORDER:
        if provider in service.providers:
            return provider, _default_model(settings, provider)
    return None
