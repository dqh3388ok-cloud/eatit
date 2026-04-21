from __future__ import annotations

from functools import lru_cache

from app.infra.config import get_settings, resolve_storage_dir
from app.infra.storage.base import StorageInterface
from app.infra.storage.local_backend import LocalFilesystemBackend


@lru_cache(maxsize=1)
def get_storage_backend() -> StorageInterface:
    settings = get_settings()
    storage_dir = resolve_storage_dir(settings.storage_dir, settings.app_env)
    return LocalFilesystemBackend(storage_dir=storage_dir)
