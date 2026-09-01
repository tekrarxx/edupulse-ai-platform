"""Model router (§140, ADR-022). Itself an `AIProvider`, so `AIGateway` and
every caller treat "one provider" and "an ordered list with fallback"
identically — no branch anywhere outside this file needs to know which one
it has.

Routing here is deliberately narrow: an ordered list, first-available-wins.
§140 also names cost/latency/task-complexity/tenant-config-based routing as
future possibilities — none of that exists yet because no real feature
needs it yet (§125); this is the smallest real thing that gives the local-
first-with-external-fallback shape §44 asks for ("external providers
should be optional" implies a real fallback path, not just a config knob
nothing reads).
"""
from app.ai.providers.base import AIProvider, GenerationRequest, GenerationResult, ProviderError


class ModelRouter(AIProvider):
    def __init__(self, *, providers: list[AIProvider]) -> None:
        if not providers:
            raise ValueError("ModelRouter requires at least one provider")
        self._providers = providers
        # Reflects whichever provider is currently being tried — including
        # on a fully-failed call, so AIGateway._record_usage's AIUsageRecord
        # still attributes the failure to a real provider/model, not a
        # placeholder (§65/§139: usage accounting must stay honest even on
        # failure, this is the whole reason AIUsageRecord has a
        # success=False path at all).
        self.provider_name = providers[0].provider_name
        self.model_name = providers[0].model_name

    def generate(self, request: GenerationRequest) -> GenerationResult:
        last_error: ProviderError | None = None
        for provider in self._providers:
            self.provider_name = provider.provider_name
            self.model_name = provider.model_name
            try:
                return provider.generate(request)
            except ProviderError as exc:
                last_error = exc
                continue
        assert last_error is not None  # unreachable: __init__ requires >=1 provider
        raise last_error
