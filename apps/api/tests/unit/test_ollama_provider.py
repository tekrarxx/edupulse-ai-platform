"""Offline tests for OllamaProvider's own HTTP/retry/parsing logic, using
httpx.MockTransport (no real network, no real Ollama instance) — the
standard httpx testing pattern. This verifies the code is correct without
violating the session's decision not to attempt a live Ollama call; a real
end-to-end run against an actual Ollama instance remains an open item
(ADR-015 Consequences).
"""
import httpx
import pytest

from app.ai.prompts import SkillExplanationOutput
from app.ai.providers.base import GenerationRequest, ProviderMalformedResponse, ProviderUnavailable
from app.ai.providers.ollama import OllamaProvider


def _request() -> GenerationRequest:
    return GenerationRequest(prompt="explain X", response_schema=SkillExplanationOutput, max_tokens=100, temperature=0.3)


def test_successful_generation_maps_response_fields() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"response": '{"explanation": "x", "key_points": ["a"]}', "eval_count": 42, "prompt_eval_count": 7},
        )

    provider = OllamaProvider(
        base_url="http://fake-ollama", model="test-model", timeout_seconds=1.0, transport=httpx.MockTransport(handler)
    )
    result = provider.generate(_request())

    assert result.raw_text == '{"explanation": "x", "key_points": ["a"]}'
    assert result.output_tokens == 42
    assert result.input_tokens == 7
    assert result.latency_ms >= 0


def test_missing_response_field_raises_malformed_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"eval_count": 1})  # no "response" key

    provider = OllamaProvider(
        base_url="http://fake-ollama", model="test-model", timeout_seconds=1.0, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderMalformedResponse):
        provider.generate(_request())


def test_transient_failure_then_success_retries_and_succeeds() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        if calls["count"] < 2:
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(200, json={"response": '{"explanation": "ok", "key_points": ["a"]}'})

    provider = OllamaProvider(
        base_url="http://fake-ollama", model="test-model", timeout_seconds=1.0, transport=httpx.MockTransport(handler)
    )
    result = provider.generate(_request())

    assert calls["count"] == 2
    assert result.raw_text == '{"explanation": "ok", "key_points": ["a"]}'


def test_persistent_failure_raises_after_bounded_attempts() -> None:
    calls = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        calls["count"] += 1
        raise httpx.ConnectError("connection refused", request=request)

    provider = OllamaProvider(
        base_url="http://fake-ollama", model="test-model", timeout_seconds=1.0, transport=httpx.MockTransport(handler)
    )
    with pytest.raises(ProviderUnavailable):
        provider.generate(_request())

    assert calls["count"] == 3  # bounded — the retry loop terminates, it does not retry forever
