from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


DEFAULT_DEVELOPMENT_SECRET = "change-me-in-environment"


class Settings(BaseSettings):
    app_name: str = "SaruSystems OS"
    app_version: str = "0.1.0"
    environment: str = "development"
    api_prefix: str = "/api"
    database_url: str = (
        "postgresql+psycopg://sarusystems:sarusystems@localhost:5432/sarusystems_os"
    )
    secret_key: str = DEFAULT_DEVELOPMENT_SECRET
    access_token_expire_minutes: int = 30
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_secret_key(self):
        environment = self.environment.strip().lower()
        if environment not in {"development", "test", "testing"} and (
            not self.secret_key.strip() or self.secret_key == DEFAULT_DEVELOPMENT_SECRET
        ):
            raise ValueError(
                "SECRET_KEY must be explicitly configured for non-development environments."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
