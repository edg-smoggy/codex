from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "Private Multi-Model Gateway"
    env: str = "dev"
    api_prefix: str = "/api/v1"

    secret_key: str = "change-this-secret"
    access_token_expire_minutes: int = 60
    refresh_token_expire_minutes: int = 20160

    database_url: str = "postgresql+asyncpg://app:app@localhost:5432/private_ai"
    redis_url: str = "redis://localhost:6379/0"

    openai_api_key: str = ""
    gemini_api_key: str = ""
    kimi_api_key: str = ""

    openai_base_url: str = "https://api.openai.com/v1"
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    kimi_base_url: str = "https://api.moonshot.cn/v1"

    allow_mock_provider: bool = True
    request_timeout_seconds: int = 90

    openai_models: Annotated[list[str], NoDecode] = ["gpt-4o-mini", "gpt-4.1-mini"]
    gemini_models: Annotated[list[str], NoDecode] = ["gemini-2.0-flash", "gemini-1.5-pro"]
    kimi_models: Annotated[list[str], NoDecode] = ["kimi-k2.5", "moonshot-v1-8k", "moonshot-v1-32k"]

    default_daily_token_limit: int = 250000
    default_daily_cost_limit: float = 20.0

    @field_validator("openai_models", "gemini_models", "kimi_models", mode="before")
    @classmethod
    def parse_csv_models(cls, value: Union[str, list[str]]) -> list[str]:
        if isinstance(value, str):
            return [v.strip() for v in value.split(",") if v.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
