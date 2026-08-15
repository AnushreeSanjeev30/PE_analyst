"""LLM service exceptions."""


class LLMServiceError(RuntimeError):
    """Base error for provider-independent LLM failures."""


class LLMConfigurationError(LLMServiceError):
    """Raised when a provider has not been configured."""


class LLMProviderError(LLMServiceError):
    """Raised when a remote provider rejects or fails a request."""
