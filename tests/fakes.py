"""Test fakes / doubles for LLM-related tests — Module F Step 29."""

from __future__ import annotations

import json
from typing import Any

from nettriage.llm.base import LLMClient, LLMRawResponse
from nettriage.llm.errors import (
    LLMEmptyResponseError,
    LLMOutputParseError,
    LLMOutputValidationError,
    LLMProviderError,
    LLMRateLimitError,
)


class FakeLLMClient:
    """Configurable fake LLM client — never calls a real API.

    Supports multiple response modes for testing different code paths:

    - ``"success"`` — returns a well-formed JSON classification output.
    - ``"invalid_json"`` — returns a string that is not valid JSON.
    - ``"empty_content"`` — raises ``LLMEmptyResponseError``.
    - ``"provider_error"`` — raises ``LLMProviderError``.
    """

    _DEFAULT_CONTENT: dict[str, Any] = {
        "primary_category": "HIGH_LATENCY",
        "secondary_categories": ["BANDWIDTH_DEGRADATION"],
        "confidence": 0.85,
        "category_scores": {
            "HIGH_LATENCY": 0.85,
            "BANDWIDTH_DEGRADATION": 0.60,
            "DNS_FAILURE": 0.30,
        },
        "key_symptoms": ["latency spikes"],
        "summary": "Test fault summary.",
        "troubleshooting_steps": [
            "Check latency",
            "Verify bandwidth",
        ],
    }

    def __init__(
        self,
        *,
        response_mode: str = "success",
        custom_content: dict[str, Any] | None = None,
        latency_ms: int = 42,
    ) -> None:
        """Initialise the fake client.

        Args:
            response_mode: One of ``"success"``, ``"invalid_json"``,
                ``"empty_content"``, ``"provider_error"``.
            custom_content: Dict to serialise as JSON for ``"success"`` mode.
                When ``None`` the default content is used.
            latency_ms: Simulated response latency.
        """
        self._mode = response_mode
        self._content = (
            custom_content if custom_content is not None else dict(self._DEFAULT_CONTENT)
        )
        self._latency_ms = latency_ms

    async def classify_fault(self, description: str) -> LLMRawResponse:
        """Simulate a classification call.

        Args:
            description: The fault description (ignored by the fake).

        Returns:
            An ``LLMRawResponse`` for ``"success"`` mode.

        Raises:
            LLMEmptyResponseError: For ``"empty_content"`` mode.
            LLMProviderError: For ``"provider_error"`` mode.
        """
        if self._mode == "provider_error":
            raise LLMProviderError("Simulated provider error")

        if self._mode == "empty_content":
            raise LLMEmptyResponseError("Simulated empty response")

        content: str
        if self._mode == "invalid_json":
            content = "this is not json"
        else:
            content = json.dumps(self._content, ensure_ascii=False)

        return LLMRawResponse(
            content=content,
            model="fake-model",
            latency_ms=self._latency_ms,
            request_id="fake-req-001",
        )


__all__ = [
    "FakeLLMClient",
    "LLMClient",
    "LLMRawResponse",
    "LLMEmptyResponseError",
    "LLMOutputParseError",
    "LLMOutputValidationError",
    "LLMProviderError",
    "LLMRateLimitError",
]
