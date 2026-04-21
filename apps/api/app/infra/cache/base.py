from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class CacheInterface(ABC):
    @abstractmethod
    async def get(self, key: str) -> Any | None:
        raise NotImplementedError

    @abstractmethod
    async def set(self, key: str, value: Any, ttl_seconds: int | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def incr(self, key: str, amount: int = 1) -> int:
        raise NotImplementedError

    @abstractmethod
    async def expire(self, key: str, ttl_seconds: int) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def ttl(self, key: str) -> int | None:
        raise NotImplementedError
