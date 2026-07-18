"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration for the Daily Sketch backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = Field(default="local", alias="APP_ENV")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    api_public_url: str = Field(default="http://localhost:8000", alias="API_PUBLIC_URL")

    database_url: str = Field(
        default="postgresql+asyncpg://dailysketch:dailysketch@localhost:5432/dailysketch",
        alias="DATABASE_URL",
    )

    storage_endpoint: str = Field(default="http://localhost:9000", alias="STORAGE_ENDPOINT")
    storage_region: str = Field(default="us-east-1", alias="STORAGE_REGION")
    storage_bucket: str = Field(default="dailysketch-local-media", alias="STORAGE_BUCKET")
    storage_access_key: str = Field(default="minioadmin", alias="STORAGE_ACCESS_KEY")
    storage_secret_key: str = Field(default="minioadmin", alias="STORAGE_SECRET_KEY")
    storage_use_ssl: bool = Field(default=False, alias="STORAGE_USE_SSL")

    descope_project_id: str = Field(default="replace-me", alias="DESCOPE_PROJECT_ID")
    descope_issuer: str = Field(
        default="https://api.descope.com/v1/apps/replace-me",
        alias="DESCOPE_ISSUER",
    )
    descope_audience: str = Field(default="replace-me", alias="DESCOPE_AUDIENCE")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
