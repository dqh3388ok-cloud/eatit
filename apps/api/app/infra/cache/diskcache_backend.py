from __future__ import annotations

from math import ceil
from pathlib import Path
from time import time
from typing import Any

import anyio
from diskcache import Cache

from app.infra.cache.base import CacheInterface


class DiskcacheBackend(CacheInterface):
    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        self._cache = Cache(str(self._cache_dir))

    async def get(self, key: str) -> Any | None:
        return await anyio.to_thread.run_sync(self._cache.get, key)

    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        await anyio.to_thread.run_sync(self._cache.set, key, value, ttl_seconds)

    async def delete(self, key: str) -> bool:
        return bool(await anyio.to_thread.run_sync(self._cache.delete, key))

    async def exists(self, key: str) -> bool:
        return await anyio.to_thread.run_sync(lambda: key in self._cache)

    async def incr(self, key: str, amount: int = 1) -> int:
        return int(await anyio.to_thread.run_sync(self._cache.incr, key, amount))

    async def expire(self, key: str, ttl_seconds: int) -> bool:
        return bool(await anyio.to_thread.run_sync(self._cache.touch, key, ttl_seconds))

    async def ttl(self, key: str) -> int | None:
        def _ttl() -> int | None:
            value = self._cache.get(key, default=None, expire_time=True)
            if value is None:
                return None
            _, expire_time = value
            if expire_time is None:
                return None
            remaining = ceil(expire_time - time())
            return max(0, remaining)

        return await anyio.to_thread.run_sync(_ttl)
