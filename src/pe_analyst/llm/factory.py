"""Settings-based construction for the enabled LLM provider registry."""

from __future__ import annotations

from pe_analyst.core.config import Settings

from .models import LLMProviderName
from .providers import (
    AnthropicProvider,
    GeminiProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
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
    if include_ollama:
        providers[LLMProviderName.OLLAMA] = OllamaProvider(
            settings.ollama_base_url, settings.llm_timeout_seconds
        )
    return LLMService(providers)
