"""Application configuration loaded from environment variables (12-factor style)."""

from functools import lru_cache

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = Field(default="development", pattern="^(development|production|test)$")
    database_url: str = "sqlite:///./prospect.db"
    # SecretStr prevents the token from being printed in logs or reprs by accident.
    github_token: SecretStr | None = None
    github_api_url: str = "https://api.github.com"
    cors_origins: str = "http://localhost:5173,http://localhost:8080"
    analysis_window_days: int = Field(default=365, ge=90, le=730)
    cache_ttl_minutes: int = Field(default=30, ge=0, le=1440)
    max_pages_per_endpoint: int = Field(default=5, ge=1, le=20)
    pr_detail_sample: int = Field(default=15, ge=0, le=100)
    author_hash_salt: SecretStr = SecretStr("prospect-default-salt")
    risk_config_path: str | None = None
    model_path: str = "app/ml/artifacts/dormancy_model.joblib"

    @field_validator("github_token", mode="before")
    @classmethod
    def empty_token_is_none(cls, value):
        return None if value in ("", None) else value

    @field_validator("database_url")
    @classmethod
    def use_psycopg_driver(cls, value: str) -> str:
        """Hosting platforms hand out postgres:// or postgresql:// URLs; SQLAlchemy needs the psycopg driver name."""
        for prefix in ("postgres://", "postgresql://"):
            if value.startswith(prefix):
                return "postgresql+psycopg://" + value[len(prefix):]
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
