"""A generic OpenAI Chat-Completions-API-compatible provider (§43, §140).
Named for the API shape, not a vendor — this same client works against
OpenAI itself, and any of the many providers implementing the identical
`/chat/completions` contract (Groq, Together, Fireworks, OpenRouter,
DeepSeek, a self-hosted vLLM/LM Studio instance, etc.), via `base_url`.
This is what makes a "small/large external model" tier of §48's cost
ladder a configuration choice, not a code change — the same discipline
ADR-015 already established for swapping Ollama's own `base_url`.

Mirrors OllamaProvider's shape exactly (same retry/timeout/error-mapping
structure) so `AIGateway` and `ModelRouter` (app/ai/router.py) treat every
provider identically — this is reviewed, production-shaped code, but per
the same explicit decision ADR-015 made for Ollama, it has never been
exercised against a real API key. Verifying it live is an open item for
whichever deployment first configures a real `secondary_ai_provider_*`
value, not something the automated test suite does (§86).
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


class OpenAICompatibleProvider(AIProvider):
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout_seconds: float,
        provider_name: str = "openai_compatible",
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.provider_name = provider_name
        self.model_name = model
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout_seconds = timeout_seconds
        # Test seam only, same convention as OllamaProvider — never set
        # outside tests. Production code always leaves this None.
        self._transport = transport

    def generate(self, request: GenerationRequest) -> GenerationResult:
        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": request.prompt}],
            "response_format": {"type": "json_object"},
            "max_tokens": request.max_tokens,
            "temperature": request.temperature,
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}

        last_error: ProviderError | None = None
        for attempt in range(_MAX_ATTEMPTS):
            started_at = time.monotonic()
            try:
                with httpx.Client(timeout=self._timeout_seconds, transport=self._transport) as client:
                    response = client.post(f"{self._base_url}/chat/completions", json=payload, headers=headers)
                response.raise_for_status()
                body = response.json()
            except httpx.TimeoutException as exc:
                last_error = ProviderTimeout(str(exc))
            except httpx.HTTPStatusError as exc:
                # A 429/5xx from the provider is transport-level unavailability
                # (§43), not a schema/content problem — distinct from
                # AIGateway's own SchemaValidationError.
                last_error = ProviderUnavailable(str(exc))
            except httpx.HTTPError as exc:
                last_error = ProviderUnavailable(str(exc))
            except ValueError as exc:  # response.json() decode failure
                last_error = ProviderMalformedResponse(str(exc))
            else:
                latency_ms = int((time.monotonic() - started_at) * 1000)
                try:
                    content = body["choices"][0]["message"]["content"]
                except (KeyError, IndexError, TypeError) as exc:
                    raise ProviderMalformedResponse("response missing choices[0].message.content") from exc
                usage = body.get("usage") or {}
                return GenerationResult(
                    raw_text=content,
                    input_tokens=usage.get("prompt_tokens"),
                    output_tokens=usage.get("completion_tokens"),
                    latency_ms=latency_ms,
                )

            if attempt < _MAX_ATTEMPTS - 1:
                time.sleep(_RETRY_DELAY_SECONDS * (attempt + 1))

        raise last_error
