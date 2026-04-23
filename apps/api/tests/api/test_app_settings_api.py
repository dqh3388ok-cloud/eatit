from __future__ import annotations

from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.infra.db import get_async_session
from app.main import app
from app.models import Base


@pytest_asyncio.fixture
async def sqlite_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield factory
    finally:
        await engine.dispose()


@pytest.fixture
def override_db(sqlite_session_factory):
    async def _override() -> AsyncIterator[AsyncSession]:
        async with sqlite_session_factory() as s:
            yield s

    app.dependency_overrides[get_async_session] = _override
    try:
        yield
    finally:
        app.dependency_overrides.pop(get_async_session, None)


async def test_get_missing_setting_returns_404(override_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/app-settings/onboarding_completed_at")

    assert response.status_code == 404
    assert response.json()["detail"] == "not set"


async def test_put_then_get_roundtrip(override_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        put_response = await client.put(
            "/api/v1/app-settings/onboarding_completed_at",
            json={"value": "2026-04-23T09:17:00+00:00"},
        )
        get_response = await client.get("/api/v1/app-settings/onboarding_completed_at")

    assert put_response.status_code == 200
    assert put_response.json() == {"value": "2026-04-23T09:17:00+00:00"}
    assert get_response.status_code == 200
    assert get_response.json() == {"value": "2026-04-23T09:17:00+00:00"}


async def test_put_rejects_non_whitelisted_key(override_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/v1/app-settings/something_else",
            json={"value": "anything"},
        )

    assert response.status_code == 400
    assert "not an allowed" in response.json()["detail"].lower()


async def test_put_rejects_secret_shaped_value(override_db) -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.put(
            "/api/v1/app-settings/last_selected_provider_hint",
            json={"value": {"provider": "openai", "api_key": "sk-leaked"}},
        )

    assert response.status_code == 400
    assert "secret" in response.json()["detail"].lower()
