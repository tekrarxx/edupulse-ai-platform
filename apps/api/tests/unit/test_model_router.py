"""ModelRouter (§140, ADR-022) — fallback ordering, in isolation from any
real transport. Uses the same FakeProvider double as test_ai_gateway.py.
"""
import pytest

from app.ai.providers.base import AIProvider, GenerationRequest, GenerationResult, ProviderTimeout, ProviderUnavailable
from app.ai.prompts import SKILL_EXPLANATION_V1
from app.ai.router import ModelRouter


class FakeProvider(AIProvider):
    def __init__(self, name: str, *, outcome) -> None:
        self.provider_name = name
        self.model_name = f"{name}-model"
        self._outcome = outcome
        self.call_count = 0

    def generate(self, request: GenerationRequest) -> GenerationResult:
        self.call_count += 1
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return GenerationResult(raw_text=self._outcome, input_tokens=1, output_tokens=1, latency_ms=1)


def _request() -> GenerationRequest:
    return GenerationRequest(prompt="x", response_schema=SKILL_EXPLANATION_V1.response_schema, max_tokens=10, temperature=0.1)


def test_uses_the_primary_provider_when_it_succeeds() -> None:
    primary = FakeProvider("primary", outcome='{"explanation": "a", "key_points": ["p"]}')
    secondary = FakeProvider("secondary", outcome='{"explanation": "b", "key_points": ["p"]}')
    router = ModelRouter(providers=[primary, secondary])

    result = router.generate(_request())

    assert result.raw_text == '{"explanation": "a", "key_points": ["p"]}'
    assert primary.call_count == 1
    assert secondary.call_count == 0
    assert router.provider_name == "primary"
    assert router.model_name == "primary-model"


def test_falls_back_to_the_secondary_provider_when_the_primary_raises_a_provider_error() -> None:
    primary = FakeProvider("primary", outcome=ProviderTimeout("simulated timeout"))
    secondary = FakeProvider("secondary", outcome='{"explanation": "b", "key_points": ["p"]}')
    router = ModelRouter(providers=[primary, secondary])

    result = router.generate(_request())

    assert result.raw_text == '{"explanation": "b", "key_points": ["p"]}'
    assert primary.call_count == 1
    assert secondary.call_count == 1
    # §65/§139: provider_name reflects whoever actually served the request,
    # so AIUsageRecord attributes correctly.
    assert router.provider_name == "secondary"
    assert router.model_name == "secondary-model"


def test_raises_the_last_providers_error_when_every_provider_fails() -> None:
    primary = FakeProvider("primary", outcome=ProviderTimeout("primary down"))
    secondary = FakeProvider("secondary", outcome=ProviderUnavailable("secondary down too"))
    router = ModelRouter(providers=[primary, secondary])

    with pytest.raises(ProviderUnavailable):
        router.generate(_request())

    assert primary.call_count == 1
    assert secondary.call_count == 1
    # Even on total failure, provider_name reflects the last one actually
    # tried — an AIUsageRecord written for this failure is still honest
    # about which provider it was.
    assert router.provider_name == "secondary"


def test_single_provider_router_just_delegates() -> None:
    only = FakeProvider("only", outcome='{"explanation": "a", "key_points": ["p"]}')
    router = ModelRouter(providers=[only])

    result = router.generate(_request())

    assert result.raw_text == '{"explanation": "a", "key_points": ["p"]}'
    assert router.provider_name == "only"


def test_requires_at_least_one_provider() -> None:
    with pytest.raises(ValueError):
        ModelRouter(providers=[])
