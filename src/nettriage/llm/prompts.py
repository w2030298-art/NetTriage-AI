"""Classification prompts for DeepSeek LLM — Module F Step 26."""

from __future__ import annotations

import hashlib

CLASSIFICATION_SYSTEM_PROMPT: str = """\
You are a telecom network trouble-ticket classification engine.

Analyze the fault description and classify it according to the following rules:

**Categories (from FaultCategory enum):**
COVERAGE_ISSUE, DROPPED_CONNECTION, HIGH_LATENCY, DNS_FAILURE, AUTH_FAILURE,
DEVICE_FAILURE, WEAK_SIGNAL, CONFIG_ERROR, PACKET_LOSS, BANDWIDTH_DEGRADATION,
SERVICE_OUTAGE, CUSTOMER_PREMISES_ISSUE, UNKNOWN

**Instructions:**
1. Determine the single most likely primary_category from the FaultCategory enum above.
2. List up to 3 secondary_categories that may also be relevant (can be empty list).
3. Assign a confidence score (0.0-1.0) for the primary classification.
4. Provide category_scores as a dict mapping each FaultCategory value to a float 0.0-1.0.
5. Extract key_symptoms — short phrases that justify the classification.
6. Write a concise summary (max 500 chars) of the fault.
7. Suggest 1-8 ordered troubleshooting_steps (specific, actionable, in English).

**CRITICAL: Return ONLY valid JSON. No markdown, no code fences, no explanatory text.**

Example of a valid response:
{
  "primary_category": "HIGH_LATENCY",
  "secondary_categories": ["BANDWIDTH_DEGRADATION", "DNS_FAILURE"],
  "confidence": 0.87,
  "category_scores": {
    "HIGH_LATENCY": 0.87,
    "BANDWIDTH_DEGRADATION": 0.62,
    "DNS_FAILURE": 0.55,
    "COVERAGE_ISSUE": 0.12,
    "DROPPED_CONNECTION": 0.08,
    "AUTH_FAILURE": 0.01,
    "DEVICE_FAILURE": 0.05,
    "WEAK_SIGNAL": 0.30,
    "CONFIG_ERROR": 0.09,
    "PACKET_LOSS": 0.40,
    "SERVICE_OUTAGE": 0.25,
    "CUSTOMER_PREMISES_ISSUE": 0.07,
    "UNKNOWN": 0.02
  },
  "key_symptoms": ["latency spikes", "intermittent slow response", "ping times increasing"],
  "summary": "Customer reports intermittent high latency affecting multiple services.",
  "troubleshooting_steps": [
    "Check network latency from the affected endpoint using ping/traceroute",
    "Verify bandwidth utilization on the customer link for saturation",
    "Inspect DNS resolution times from the customer premises",
    "Check for packet loss using a continuous ping to the gateway",
    "Review recent configuration changes on routers in the affected segment"
  ]
}
"""


def build_classification_user_prompt(description: str) -> str:
    """Wrap a fault description in a minimal user message.

    No prompt injection: the function treats the description purely as data.
    For logging / tracing, use ``description_hash()`` instead of the raw text.

    Args:
        description: The raw fault / ticket description text.

    Returns:
        A plain user instruction string.
    """
    return (
        "Classify the following network trouble ticket description.\n\n"
        f"Description:\n{description}"
    )


def description_hash(description: str, length: int = 12) -> str:
    """Return a short SHA-256 hex hash of the description for safe logging.

    Args:
        description: The description text to hash.
        length: Number of hex characters to return (default 12 = 48 bits).

    Returns:
        A hex digest prefix.
    """
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:length]
