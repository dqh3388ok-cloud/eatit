from __future__ import annotations

from functools import lru_cache

from app.infra.cache.base import CacheInterface
from app.infra.cache.diskcache_backend import DiskcacheBackend
from app.infra.config import get_settings, resolve_cache_dir


@lru_cache(maxsize=1)
def get_cache_backend() -> CacheInterface:
    settings = get_settings()
    cache_dir = resolve_cache_dir(settings.cache_dir, settings.app_env)
    return DiskcacheBackend(cache_dir=cache_dir)
