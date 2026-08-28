"""Real Ollama provider (ADR-015 §1). This is reviewed, production-shaped
code, but — per an explicit decision this session — it has never been
exercised against a live Ollama instance. Verifying it for real
(`docker compose up -d ollama`, pull a model, then a real
`POST /ai/explanations` call) is an open item for local/production use, not
something the automated test suite does (§86 — tests never depend on a live
network call).
"""
import time

import httpx

from app.ai.providers.base import (
    AIProvider,
    GenerationRequest,
    GenerationResult,
    ProviderError,
    ProviderMalformedResponse,
    ProviderTimeout,
    ProviderUnavailable,
)

_MAX_ATTEMPTS = 3
_RETRY_DELAY_SECONDS = 0.5


class OllamaProvider(AIProvider):
    def __init__(
        self, *, base_url: str, model: str, timeout_seconds: float, transport: httpx.BaseTransport | None = None
    ) -> None:
        self.provider_name = "ollama"
        self.model_name = model
        self._base_url = base_url.rstrip("/")
        self._timeout_seconds = timeout_seconds
        # Test seam only (the standard httpx pattern, e.g. httpx.MockTransport)
        # — never set outside tests. Production code always leaves this None,
        # which makes httpx.Client use its real network transport.
        self._transport = transport

    def generate(self, request: GenerationRequest) -> GenerationResult:
        payload = {
            "model": self.model_name,
            "prompt": request.prompt,
            "format": "json",
            "stream": False,
            "options": {"num_predict": request.max_tokens, "temperature": request.temperature},
        }

        last_error: ProviderError | None = None
        for attempt in range(_MAX_ATTEMPTS):
            started_at = time.monotonic()
            try:
                with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
                    response = client.post(f"{self._base_url}/api/generate", json=payload)
                response.raise_for_status()
                body = response.json()
            except httpx.TimeoutException as exc:
                last_error = ProviderTimeout(str(exc))
            except httpx.HTTPError as exc:
                last_error = ProviderUnavailable(str(exc))
            except ValueError as exc:  # response.json() decode failure
                last_error = ProviderMalformedResponse(str(exc))
            else:
                latency_ms = int((time.monotonic() - started_at) * 1000)
                if "response" not in body:
                    raise ProviderMalformedResponse("Ollama response missing 'response' field")
                return GenerationResult(
                    raw_text=body["response"],
                    input_tokens=body.get("prompt_eval_count"),
                    output_tokens=body.get("eval_count"),
                    latency_ms=latency_ms,
                )

            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY_SECONDS * (attempt + 1))

        raise last_error
