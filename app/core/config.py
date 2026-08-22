from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, sourced from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "KJBN Food Trucks API"
    environment: str = Field(default="development")
    log_level: str = Field(default="INFO")

    # DataSF (Socrata) Mobile Food Facility Permit dataset
    datasf_base_url: str = Field(default="https://data.sfgov.org/resource/rqzj-sfat.json")
    datasf_app_token: str | None = Field(default=None)
    datasf_timeout_seconds: float = Field(default=8.0)
    datasf_max_retries: int = Field(default=3)

    # In-memory cache TTL for the truck dataset
    cache_ttl_seconds: int = Field(default=900)

    # Search defaults
    default_radius_km: float = Field(default=1.0)
    max_radius_km: float = Field(default=10.0)
    max_results: int = Field(default=50)

    cors_allow_origins: list[str] = Field(default_factory=lambda: ["*"])


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton so we parse the environment only once."""
    return Settings()
