from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.engine import URL, make_url
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine

from app.infra.config import get_settings, resolve_database_url


settings = get_settings()
database_url = resolve_database_url(settings.database_url)


def _ensure_sqlite_parent_dir(url: URL) -> None:
    if url.get_backend_name() != "sqlite" or url.database in (None, "", ":memory:"):
        return
    Path(url.database).parent.mkdir(parents=True, exist_ok=True)


def _configure_sqlite_pragmas(dbapi_connection, _) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def build_async_engine(url: str, **kwargs) -> AsyncEngine:
    parsed_url = make_url(url)
    _ensure_sqlite_parent_dir(parsed_url)
    engine = create_async_engine(url, future=True, **kwargs)
    if parsed_url.get_backend_name() == "sqlite":
        event.listen(engine.sync_engine, "connect", _configure_sqlite_pragmas)
    return engine


engine = build_async_engine(database_url)
AsyncSessionFactory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionFactory() as session:
        yield session
