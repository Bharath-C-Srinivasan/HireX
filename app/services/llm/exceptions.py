"""Exceptions for LLM adapters."""

class LLMAdapterError(Exception):
    """Base exception for LLM adapter errors."""
    pass


class LLMTimeoutError(LLMAdapterError):
    """Raised when the LLM call times out."""
    pass


class LLMMalformedOutputError(LLMAdapterError):
    """Raised when the LLM returns invalid JSON or schema violations."""
    pass


class LLMRateLimitError(LLMAdapterError):
    """Raised when LLM API rate limit is exceeded."""
    pass


class PromptInjectionDetectedWarning(LLMAdapterError):
    """Raised/Logged when prompt injection attempts are detected in candidate input."""
    pass
