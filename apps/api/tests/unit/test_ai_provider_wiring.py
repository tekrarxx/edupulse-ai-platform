"""get_ai_provider's own routing decision (§140, ADR-022): Ollama alone by
default, a ModelRouter only when every secondary-provider setting is
actually configured. Exercises the real function against a real Settings
object (env vars monkeypatched) — not a live network call either way,
since AIProvider.__init__ never connects to anything.
"""
from app.api.deps import get_ai_provider
from app.ai.providers.ollama import OllamaProvider
from app.ai.router import ModelRouter
from app.core.config import get_settings


def _clear_settings_cache() -> None:
    get_settings.cache_clear()


def test_defaults_to_ollama_alone_when_no_secondary_provider_is_configured(monkeypatch) -> None:
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_BASE_URL", raising=False)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_MODEL", raising=False)
    _clear_settings_cache()

    provider = get_ai_provider()

    assert isinstance(provider, OllamaProvider)
    _clear_settings_cache()


def test_returns_a_model_router_when_all_three_secondary_settings_are_present(monkeypatch) -> None:
    monkeypatch.setenv("SECONDARY_AI_PROVIDER_BASE_URL", "https://api.example.com/v1")
    monkeypatch.setenv("SECONDARY_AI_PROVIDER_API_KEY", "fake-key")
    monkeypatch.setenv("SECONDARY_AI_PROVIDER_MODEL", "fake-model")
    _clear_settings_cache()

    provider = get_ai_provider()

    assert isinstance(provider, ModelRouter)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_BASE_URL", raising=False)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_MODEL", raising=False)
    _clear_settings_cache()


def test_stays_ollama_alone_when_only_some_secondary_settings_are_present(monkeypatch) -> None:
    """§44/§136: no partial/accidental external config — all three or none."""
    monkeypatch.setenv("SECONDARY_AI_PROVIDER_BASE_URL", "https://api.example.com/v1")
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_API_KEY", raising=False)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_MODEL", raising=False)
    _clear_settings_cache()

    provider = get_ai_provider()

    assert isinstance(provider, OllamaProvider)
    monkeypatch.delenv("SECONDARY_AI_PROVIDER_BASE_URL", raising=False)
    _clear_settings_cache()
