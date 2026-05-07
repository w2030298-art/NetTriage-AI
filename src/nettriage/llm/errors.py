"""LLM-specific exception hierarchy — Module F Step 25."""

from __future__ import annotations


class LLMError(Exception):
    """Base exception for all LLM-related errors."""


class LLMTimeoutError(LLMError):
    """The provider did not respond within the configured timeout."""


class LLMRateLimitError(LLMError):
    """The provider returned a rate-limit (429 / throttling) status."""


class LLMEmptyResponseError(LLMError):
    """The provider returned a successful HTTP response with empty content."""


class LLMProviderError(LLMError):
    """Generic / unexpected provider-side error (e.g. 5xx)."""


class LLMOutputParseError(LLMError):
    """Failed to parse the raw LLM response as valid JSON."""


class LLMOutputValidationError(LLMError):
    """The parsed JSON failed Pydantic schema validation."""
