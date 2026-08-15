"""HTTP implementations for supported model providers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from .exceptions import LLMConfigurationError, LLMProviderError
from .models import LLMProviderName, LLMRequest, LLMResponse


class LLMProvider(ABC):
    name: LLMProviderName

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse: ...

    @staticmethod
    def _raise(response: httpx.Response) -> None:
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as error:
            raise LLMProviderError(
                f"Provider request failed: {error.response.status_code} {error.response.text}"
            ) from error


class OpenAIProvider(LLMProvider):
    name = LLMProviderName.OPENAI

    def __init__(self, api_key: str | None, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise LLMConfigurationError("OPENAI_API_KEY is not configured")
        self.client = httpx.Client(
            base_url="https://api.openai.com/v1",
            timeout=timeout_seconds,
            headers={"Authorization": f"Bearer {api_key}"},
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model,
            "input": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "temperature": request.temperature,
            "max_output_tokens": request.max_output_tokens,
            "store": False,
        }
        if request.system_prompt:
            payload["instructions"] = request.system_prompt
        if request.response_schema:
            payload["text"] = {
                "format": {
                    "type": "json_schema",
                    "name": "response",
                    "schema": request.response_schema,
                    "strict": True,
                }
            }
        response = self.client.post("/responses", json=payload)
        self._raise(response)
        body = response.json()
        usage = body.get("usage", {})
        return LLMResponse(
            body.get("output_text", ""),
            self.name,
            request.model,
            body.get("id"),
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            body,
        )


class AnthropicProvider(LLMProvider):
    name = LLMProviderName.ANTHROPIC

    def __init__(self, api_key: str | None, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise LLMConfigurationError("ANTHROPIC_API_KEY is not configured")
        self.client = httpx.Client(
            base_url="https://api.anthropic.com/v1",
            timeout=timeout_seconds,
            headers={"x-api-key": api_key, "anthropic-version": "2023-06-01"},
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": message.role, "content": message.content} for message in request.messages
            ],
            "temperature": request.temperature,
            "max_tokens": request.max_output_tokens,
        }
        if request.system_prompt:
            payload["system"] = request.system_prompt
        response = self.client.post("/messages", json=payload)
        self._raise(response)
        body = response.json()
        text = "".join(
            item.get("text", "") for item in body.get("content", []) if item.get("type") == "text"
        )
        usage = body.get("usage", {})
        return LLMResponse(
            text,
            self.name,
            request.model,
            body.get("id"),
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            body,
        )


class GeminiProvider(LLMProvider):
    name = LLMProviderName.GEMINI

    def __init__(self, api_key: str | None, timeout_seconds: float = 60.0) -> None:
        if not api_key:
            raise LLMConfigurationError("GEMINI_API_KEY is not configured")
        self.api_key = api_key
        self.client = httpx.Client(
            base_url="https://generativelanguage.googleapis.com/v1beta", timeout=timeout_seconds
        )

    def generate(self, request: LLMRequest) -> LLMResponse:
        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "model" if message.role == "assistant" else "user",
                    "parts": [{"text": message.content}],
                }
                for message in request.messages
            ],
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_output_tokens,
            },
        }
        if request.system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": request.system_prompt}]}
        response = self.client.post(
            f"/models/{request.model}:generateContent", params={"key": self.api_key}, json=payload
        )
        self._raise(response)
        body = response.json()
        text = "".join(
            part.get("text", "")
            for candidate in body.get("candidates", [])
            for part in candidate.get("content", {}).get("parts", [])
        )
        usage = body.get("usageMetadata", {})
        return LLMResponse(
            text,
            self.name,
            request.model,
            None,
            usage.get("promptTokenCount"),
            usage.get("candidatesTokenCount"),
            body,
        )


class OllamaProvider(LLMProvider):
    name = LLMProviderName.OLLAMA

    def __init__(self, base_url: str, timeout_seconds: float = 60.0) -> None:
        self.client = httpx.Client(base_url=base_url.rstrip("/"), timeout=timeout_seconds)

    def generate(self, request: LLMRequest) -> LLMResponse:
        messages = [
            {"role": message.role, "content": message.content} for message in request.messages
        ]
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})
        response = self.client.post(
            "/api/chat",
            json={
                "model": request.model,
                "messages": messages,
                "stream": False,
                "options": {"temperature": request.temperature},
            },
        )
        self._raise(response)
        body = response.json()
        return LLMResponse(
            body.get("message", {}).get("content", ""),
            self.name,
            request.model,
            None,
            body.get("prompt_eval_count"),
            body.get("eval_count"),
            body,
        )
