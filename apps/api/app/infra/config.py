from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


ROOT_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
API_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "eatit-api"
    app_version: str = "0.1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = "postgresql+asyncpg://eatit:eatit_dev_password@localhost:5432/eatit"
    redis_url: str = "redis://localhost:6379/0"
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "eatitminio"
    minio_secret_key: str = "eatitminio123"
    minio_bucket: str = "eatit-dev"
    llm_api_key: str = ""
    deepgram_api_key: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(
        env_file=(ROOT_ENV_PATH, API_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
