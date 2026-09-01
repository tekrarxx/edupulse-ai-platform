"""Offline tests for OpenAICompatibleProvider's HTTP/retry/parsing logic,
using httpx.MockTransport — mirrors test_ollama_provider.py's pattern
exactly. A real end-to-end run against a live API key remains an open item
(ADR-022), same as Ollama's own equivalent note in ADR-015.
"""
import httpx
import pytest

from app.ai.prompts import SkillExplanationOutput
from app.ai.providers.base import GenerationRequest, ProviderMalformedResponse, ProviderUnavailable
from app.ai.providers.openai_compatible import OpenAICompatibleProvider


def _request() -> GenerationRequest:
    return GenerationRequest(prompt="explain X", response_schema=SkillExplanationOutput, max_tokens=100, temperature=0.3)


def _provider(handler) -> OpenAICompatibleProvider:
    return OpenAICompatibleProvider(
        base_url="http://fake-provider",
        api_key="fake-key",
        model="test-model",
        timeout_seconds=1.0,
        provider_name="fake-openai-compatible",
        transport=httpx.MockTransport(handler),
    )


def test_successful_generation_maps_response_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer fake-key"
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"explanation": "x", "key_points": ["a"]}'}}],
                "usage": {"prompt_tokens": 7, "completion_tokens": 42},
            },
        )

    result = _provider(handler).generate(_request())

    assert result.raw_text == '{"explanation": "x", "key_points": ["a"]}'
    assert result.input_tokens == 7
    assert result.output_tokens == 42
    assert result.latency_ms >= 0


def test_missing_choices_raises_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"usage": {}})  # no "choices" key

    with pytest.raises(ProviderMalformedResponse):
        _provider(handler).generate(_request())


def test_non_2xx_status_raises_provider_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, json={"error": "rate limited"})

    with pytest.raises(ProviderUnavailable):
        _provider(handler).generate(_request())

    # Bounded retries even on a real HTTP error status, same discipline as
    # OllamaProvider's connection-failure retries.


def test_transient_failure_then_success_retries_and_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"choices": [{"message": {"content": '{"explanation": "ok", "key_points": ["a"]}'}}]})

    result = _provider(handler).generate(_request())

    assert calls["count"] == 2
    assert result.raw_text == '{"explanation": "ok", "key_points": ["a"]}'


def test_persistent_failure_raises_after_bounded_attempts() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ProviderUnavailable):
        _provider(handler).generate(_request())

    assert calls["count"] == 3  # bounded — does not retry forever
