from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, read from environment variables (§108).

    No secret gets a hardcoded default that would be usable outside of local
    development; `api_secret_key` still defaults so the skeleton runs out of
    the box, but the value is an obvious placeholder, not a real secret.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"

    database_url: str = "postgresql+psycopg://edupulse:edupulse@localhost:5432/edupulse"
    redis_url: str = "redis://localhost:6379/0"

    api_cors_origins: str = "http://localhost:3000"
    api_secret_key: str = "change-me-in-local-env"

    # §44 local-first AI. Not started/pulled by default — see ADR-015.
    # llama3.2:1b, not an 8B model: real-hardware testing on a modest
    # 4-core/8-thread mobile CPU with no usable GPU acceleration (ADR-015
    # addendum) found an 8B model impractical on that class of machine —
    # 1-3B is the realistic default for CPU-only local dev.
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.2:1b"
    ai_request_timeout_seconds: float = 30.0

    # §9-11 local-first: a local Mailpit SMTP catcher by default (see
    # docker-compose.yml), never a real provider/API key out of the box.
    # Swapping to a real transactional-email provider for production is a
    # deliberate later decision (§119), not something app code should assume.
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from_address: str = "no-reply@edupulse.local"
    # Used only to build the link inside password-reset emails — must be
    # reachable from the recipient's browser, never a container-internal name.
    web_base_url: str = "http://localhost:3000"

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
