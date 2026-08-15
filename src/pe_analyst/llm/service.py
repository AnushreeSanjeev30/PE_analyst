"""Provider registry and single entry point for agent LLM calls."""

from __future__ import annotations

from .models import LLMProviderName, LLMRequest, LLMResponse
from .providers import LLMProvider


class LLMService:
    def __init__(self, providers: dict[LLMProviderName, LLMProvider]) -> None:
        self.providers = providers

    def generate(self, provider: LLMProviderName, request: LLMRequest) -> LLMResponse:
        if provider not in self.providers:
            available = ", ".join(sorted(item.value for item in self.providers))
            raise ValueError(
                f"Provider '{provider.value}' is not enabled. Available: {available or 'none'}"
            )
        return self.providers[provider].generate(request)
