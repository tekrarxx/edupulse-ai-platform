"""Provider abstraction (ADR-015 §1). Application code — the AI Gateway
included — depends only on `AIProvider`, never on a concrete provider like
`OllamaProvider`. A test double implementing this same interface is how the
gateway is tested without a live network call (see tests/unit/test_ai_gateway.py).
"""
import abc
from dataclasses import dataclass

from pydantic import BaseModel


class ProviderError(Exception):
    """Transport/protocol-level failure — distinct from the gateway's own
    schema-validation or safety failures, which are not provider errors: a
    provider can return syntactically valid text that still fails the
    gateway's checks."""


class ProviderTimeout(ProviderError):
    pass


class ProviderUnavailable(ProviderError):
    pass


class ProviderMalformedResponse(ProviderError):
    """The provider's transport-level response itself was unusable (e.g. not
    valid JSON at the HTTP envelope level) — not to be confused with the
    gateway's SchemaValidationError, which is about the *generated content*
    not matching the requested schema."""


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    response_schema: type[BaseModel]
    max_tokens: int
    temperature: float


@dataclass(frozen=True)
class GenerationResult:
    raw_text: str
    # Ollama's own tokenizer counts (eval_count/prompt_eval_count) — an
    # approximation, not a billing-grade measurement (ADR-015 §1).
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: int


class AIProvider(abc.ABC):
    provider_name: str
    model_name: str

    @abc.abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult:
        """Raises a ProviderError subclass on transport/protocol failure.
        Never raises a bare Exception."""
