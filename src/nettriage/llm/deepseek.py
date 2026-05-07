"""DeepSeek API client implementing LLMClient protocol — Module F Step 27."""

from __future__ import annotations

import hashlib
import logging
import time
from typing import Any, cast

import httpx
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from nettriage.core.config import Settings
from nettriage.llm.base import LLMRawResponse
from nettriage.llm.errors import (
    LLMEmptyResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)

logger = logging.getLogger(__name__)


def _description_hash(description: str) -> str:
    return hashlib.sha256(description.encode("utf-8")).hexdigest()[:12]


class DeepSeekClient:
    """Async client for the DeepSeek chat completions API.

    Implements the ``LLMClient`` protocol.
    """

    def __init__(
        self,
        settings: Settings,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        """Initialise the client.

        Args:
            settings: Application settings (API key, base URL, model, etc.).
            http_client: Optional pre-configured ``httpx.AsyncClient``.
                If ``None``, a default client will be created at call time.
        """
        self._settings = settings
        self._http_client = http_client

    async def classify_fault(self, description: str) -> LLMRawResponse:
        """Send a classification request to the DeepSeek API.

        Args:
            description: The free-text fault description to classify.

        Returns:
            An ``LLMRawResponse`` with the raw JSON content.

        Raises:
            LLMRateLimitError: On HTTP 429.
            LLMTimeoutError: On request timeout.
            LLMEmptyResponseError: When the API returns empty content.
            LLMProviderError: On other non-2xx responses.
        """
        desc_hash = _description_hash(description)
        logger.debug("Sending classify request — desc_hash=%s", desc_hash)

        client = self._http_client or httpx.AsyncClient()

        body = self._build_request_body(description)

        try:
            retryer = AsyncRetrying(
                retry=retry_if_exception_type(
                    (LLMRateLimitError, LLMProviderError, LLMTimeoutError)
                ),
                stop=stop_after_attempt(self._settings.deepseek_max_retries + 1),
                wait=wait_exponential(multiplier=1, min=1, max=30),
                reraise=True,
            )
            result: LLMRawResponse = cast(
                LLMRawResponse,
                await retryer(self._execute_request, client, body, desc_hash),
            )
        finally:
            if self._http_client is None:
                # Only close if we created the client ourselves
                await client.aclose()

        return result

    async def _execute_request(
        self,
        client: httpx.AsyncClient,
        body: dict[str, Any],
        desc_hash: str,
    ) -> LLMRawResponse:
        """Core HTTP call — may be retried by tenacity AsyncRetrying."""
        api_key = self._settings.deepseek_api_key
        if api_key is None:
            raise LLMProviderError("DeepSeek API key is not configured")

        url = f"{self._settings.deepseek_base_url.rstrip('/')}/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }

        start = time.perf_counter()

        try:
            response = await client.post(
                url,
                json=body,
                headers=headers,
                timeout=float(self._settings.deepseek_timeout_seconds),
            )
        except httpx.TimeoutException as exc:
            logger.warning("DeepSeek request timed out — desc_hash=%s", desc_hash)
            raise LLMTimeoutError(
                f"Request to {url} timed out after "
                f"{self._settings.deepseek_timeout_seconds}s"
            ) from exc

        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if response.status_code == 429:
            logger.warning("DeepSeek rate-limited — desc_hash=%s", desc_hash)
            raise LLMRateLimitError(
                f"Rate limited by DeepSeek API (429) after {elapsed_ms}ms"
            )

        if response.status_code >= 500:
            logger.warning(
                "DeepSeek server error %d — desc_hash=%s",
                response.status_code,
                desc_hash,
            )
            raise LLMProviderError(
                f"DeepSeek API returned {response.status_code}"
            )

        if response.status_code != 200:
            raise LLMProviderError(
                f"DeepSeek API returned unexpected status {response.status_code}"
            )

        data = response.json()
        request_id: str | None = response.headers.get("x-ds-request-id")

        content = _extract_content(data)

        if not content:
            logger.warning("DeepSeek returned empty content — desc_hash=%s", desc_hash)
            raise LLMEmptyResponseError(
                f"DeepSeek returned empty content (request_id={request_id})"
            )

        logger.info(
            "DeepSeek response OK — desc_hash=%s latency=%dms model=%s",
            desc_hash,
            elapsed_ms,
            self._settings.deepseek_model,
        )

        return LLMRawResponse(
            content=content,
            model=self._settings.deepseek_model,
            latency_ms=elapsed_ms,
            request_id=request_id,
        )

    def _build_request_body(self, description: str) -> dict[str, Any]:
        """Construct the JSON body for a chat completion request."""
        from nettriage.llm.prompts import (  # noqa: PLC0415
            CLASSIFICATION_SYSTEM_PROMPT,
            build_classification_user_prompt,
        )

        return {
            "model": self._settings.deepseek_model,
            "messages": [
                {"role": "system", "content": CLASSIFICATION_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": build_classification_user_prompt(description),
                },
            ],
            "response_format": {"type": "json_object"},
            "stream": False,
        }


def _extract_content(data: dict[str, Any]) -> str:
    """Extract the message content text from a DeepSeek API response dict."""
    try:
        choices: list[dict[str, Any]] = data["choices"]
        content: object = choices[0]["message"]["content"]
        return str(content)
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMProviderError(
            f"Unexpected DeepSeek response structure: {exc}"
        ) from exc
