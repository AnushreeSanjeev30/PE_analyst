"""Provider-neutral contracts for LLM generation."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class LLMProviderName(StrEnum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GEMINI = "gemini"
    OLLAMA = "ollama"
    GROQ = "groq"
    XAI = "xai"


@dataclass(slots=True, frozen=True)
class LLMMessage:
    role: str
    content: str


@dataclass(slots=True, frozen=True)
class LLMRequest:
    messages: list[LLMMessage]
    model: str
    temperature: float = 0.2
    max_output_tokens: int = 2_000
    system_prompt: str | None = None
    response_schema: dict[str, Any] | None = None


@dataclass(slots=True, frozen=True)
class LLMResponse:
    text: str
    provider: LLMProviderName
    model: str
    request_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    raw: dict[str, Any] = field(default_factory=dict)
