"""LLM client protocol and raw response dataclass — Module F Step 25."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class LLMRawResponse:
    """Raw response from an LLM provider before parsing.

    Attributes:
        content: The raw text content returned by the LLM.
        model: The model identifier used for this inference.
        latency_ms: Measured round-trip latency in milliseconds.
        request_id: Optional provider-assigned request identifier.
    """

    content: str
    model: str
    latency_ms: int
    request_id: str | None = field(default=None)


class LLMClient(Protocol):
    """Async protocol for LLM classification providers.

    Any concrete client (DeepSeek, OpenAI, Fake) must implement
    ``classify_fault`` so the classifier service can be provider-agnostic.
    """

    async def classify_fault(self, description: str) -> LLMRawResponse:
        """Classify a network trouble ticket description.

        Args:
            description: The free-text fault / ticket description.

        Returns:
            An LLMRawResponse containing the raw output before validation.
        """
        ...
