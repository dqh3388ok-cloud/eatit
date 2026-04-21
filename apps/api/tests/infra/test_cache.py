from __future__ import annotations

from pathlib import Path

from app.infra.cache.diskcache_backend import DiskcacheBackend


async def test_diskcache_backend_crud_and_ttl(tmp_path: Path) -> None:
    cache = DiskcacheBackend(tmp_path / "cache")

    assert await cache.get("missing") is None
    assert await cache.exists("counter") is False

    await cache.set("greeting", {"value": "hello"}, ttl_seconds=30)
    assert await cache.get("greeting") == {"value": "hello"}
    assert await cache.exists("greeting") is True

    ttl = await cache.ttl("greeting")
    assert ttl is not None
    assert 0 < ttl <= 30

    assert await cache.expire("greeting", 60) is True
    extended_ttl = await cache.ttl("greeting")
    assert extended_ttl is not None
    assert 0 < extended_ttl <= 60

    assert await cache.incr("counter") == 1
    assert await cache.incr("counter", 4) == 5

    assert await cache.delete("greeting") is True
    assert await cache.get("greeting") is None
    assert await cache.delete("missing") is False


async def test_diskcache_backend_creates_directory(tmp_path: Path) -> None:
    cache_dir = tmp_path / "nested" / "cache"
    assert cache_dir.exists() is False

    cache = DiskcacheBackend(cache_dir)

    await cache.set("ready", True)
    assert cache_dir.exists() is True
    assert await cache.get("ready") is True
