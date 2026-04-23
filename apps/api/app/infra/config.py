from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[4]
ROOT_ENV_PATH = Path(__file__).resolve().parents[4] / ".env"
API_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
DEFAULT_DATABASE_URL = "sqlite+aiosqlite:///./.data/eatit.db"
DEFAULT_DEVELOPMENT_CACHE_DIR = ".data/cache"
DEFAULT_PRODUCTION_CACHE_DIR = "~/Library/Application Support/Eatit/cache"
DEFAULT_DEVELOPMENT_STORAGE_DIR = ".data/storage"
DEFAULT_PRODUCTION_STORAGE_DIR = "~/Library/Application Support/Eatit/storage"


class Settings(BaseSettings):
    app_env: str = "development"
    app_name: str = "eatit-api"
    app_version: str = "0.1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    database_url: str = DEFAULT_DATABASE_URL
    cache_dir: str | None = None
    storage_dir: str | None = None
    deepgram_api_key: str = ""
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"
    sentry_dsn: str = ""

    model_config = SettingsConfigDict(
        env_file=(ROOT_ENV_PATH, API_ENV_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def resolve_database_url(database_url: str) -> str:
    relative_prefix = "sqlite+aiosqlite:///./"
    if database_url.startswith(relative_prefix):
        relative_path = database_url.removeprefix(relative_prefix)
        resolved_path = (PROJECT_ROOT / relative_path).resolve()
        return f"sqlite+aiosqlite:///{resolved_path.as_posix()}"
    return database_url


def resolve_cache_dir(cache_dir: str | None, app_env: str) -> Path:
    raw_path = cache_dir or (
        DEFAULT_DEVELOPMENT_CACHE_DIR if app_env == "development" else DEFAULT_PRODUCTION_CACHE_DIR
    )
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path


def resolve_storage_dir(storage_dir: str | None, app_env: str) -> Path:
    raw_path = storage_dir or (
        DEFAULT_DEVELOPMENT_STORAGE_DIR
        if app_env == "development"
        else DEFAULT_PRODUCTION_STORAGE_DIR
    )
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = (PROJECT_ROOT / path).resolve()
    return path
