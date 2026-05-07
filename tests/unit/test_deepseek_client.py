"""Unit tests for DeepSeekClient using mocked httpx transport — Module F Step 29."""

from __future__ import annotations

import httpx
import pytest
from pydantic import SecretStr

from nettriage.core.config import Settings
from nettriage.llm.deepseek import DeepSeekClient
from nettriage.llm.errors import (
    LLMEmptyResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------


def _settings(**overrides: object) -> Settings:
    """Create a Settings instance with safe test defaults."""
    return Settings(
        deepseek_api_key=SecretStr("test-key-12345"),
        deepseek_base_url="https://api.deepseek.com",
        deepseek_model="deepseek-chat",
        deepseek_timeout_seconds=10,
        **overrides,  # type: ignore[arg-type]
    )


def _ok_response(content: str) -> httpx.Response:
    """Return a 200 response with a DeepSeek-shaped JSON body."""
    body = {
        "choices": [
            {
                "message": {"content": content},
                "finish_reason": "stop",
            }
        ]
    }
    return httpx.Response(200, json=body, headers={"x-ds-request-id": "req-abc"})


# ---------------------------------------------------------------------------
# Normal success
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_normal_response_returns_raw_response() -> None:
    """A 200 response with valid content returns an LLMRawResponse."""
    settings = _settings()
    transport = httpx.MockTransport(lambda req: _ok_response('{"foo": "bar"}'))
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    result = await client.classify_fault("Network is down")

    assert result.content == '{"foo": "bar"}'
    assert result.model == "deepseek-chat"
    assert result.latency_ms >= 0
    assert result.request_id == "req-abc"


# ---------------------------------------------------------------------------
# 429 rate-limit → retry → LLMRateLimitError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_429_rate_limit_raises_after_retries() -> None:
    """On repeated 429, the client retries once then raises LLMRateLimitError."""
    settings = _settings(deepseek_max_retries=1)
    transport = httpx.MockTransport(lambda req: httpx.Response(429))
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMRateLimitError, match="Rate limited"):
        await client.classify_fault("test")


# ---------------------------------------------------------------------------
# 5xx → retry → LLMProviderError
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_500_raises_provider_error_after_retries() -> None:
    """A 500 response retries once then raises LLMProviderError."""
    settings = _settings(deepseek_max_retries=1)
    transport = httpx.MockTransport(lambda req: httpx.Response(500))
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMProviderError, match="500"):
        await client.classify_fault("test")


@pytest.mark.asyncio
async def test_503_raises_provider_error_after_retries() -> None:
    """A 503 response retries once then raises LLMProviderError."""
    settings = _settings(deepseek_max_retries=1)
    transport = httpx.MockTransport(lambda req: httpx.Response(503))
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMProviderError, match="503"):
        await client.classify_fault("test")


# ---------------------------------------------------------------------------
# Empty content
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_content_raises_empty_response_error() -> None:
    """A 200 response with empty content raises LLMEmptyResponseError."""
    settings = _settings()
    transport = httpx.MockTransport(
        lambda req: httpx.Response(
            200,
            json={"choices": [{"message": {"content": ""}}]},
            headers={"x-ds-request-id": "req-empty"},
        )
    )
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMEmptyResponseError, match="empty content"):
        await client.classify_fault("test")


# ---------------------------------------------------------------------------
# Timeout
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timeout_raises_timeout_error() -> None:
    """A request that times out raises LLMTimeoutError."""

    def _timeout_handler(req: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Read timeout")

    settings = _settings()
    transport = httpx.MockTransport(_timeout_handler)
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMTimeoutError, match="timed out"):
        await client.classify_fault("test")


# ---------------------------------------------------------------------------
# Missing API key
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_api_key_raises_provider_error() -> None:
    """When deepseek_api_key is None, classify_fault raises LLMProviderError."""
    settings = Settings(deepseek_api_key=None)
    transport = httpx.MockTransport(lambda req: _ok_response("{}"))
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMProviderError, match="API key"):
        await client.classify_fault("test")


# ---------------------------------------------------------------------------
# 4xx (non-429) → no retry, immediate error
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_401_raises_provider_error_without_retry() -> None:
    """A non-retryable 4xx raises LLMProviderError immediately."""
    settings = _settings()
    transport = httpx.MockTransport(lambda req: httpx.Response(401))
    client = DeepSeekClient(settings, http_client=httpx.AsyncClient(transport=transport))

    with pytest.raises(LLMProviderError, match="401"):
        await client.classify_fault("test")
