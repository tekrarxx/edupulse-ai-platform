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

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.api_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
