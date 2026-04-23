from __future__ import annotations

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.domain.settings.service import (
    SecretPayloadRejectedError,
    UnknownSettingKeyError,
    delete_setting,
    get_setting,
    set_setting,
)
from app.models import Base


@pytest_asyncio.fixture
async def session() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as s:
        yield s
    await engine.dispose()


async def test_get_missing_key_returns_none(session: AsyncSession) -> None:
    assert await get_setting(session, "onboarding_completed_at") is None


async def test_set_and_get_roundtrip(session: AsyncSession) -> None:
    await set_setting(session, "ui_theme", "dark")

    assert await get_setting(session, "ui_theme") == "dark"


async def test_set_overwrites_existing_value(session: AsyncSession) -> None:
    await set_setting(session, "ui_theme", "light")
    await set_setting(session, "ui_theme", "dark")

    assert await get_setting(session, "ui_theme") == "dark"


async def test_set_accepts_json_objects(session: AsyncSession) -> None:
    await set_setting(session, "onboarding_completed_at", "2026-04-23T09:17:00+00:00")

    assert (
        await get_setting(session, "onboarding_completed_at")
        == "2026-04-23T09:17:00+00:00"
    )


async def test_delete_existing_returns_true(session: AsyncSession) -> None:
    await set_setting(session, "ui_theme", "dark")

    assert await delete_setting(session, "ui_theme") is True
    assert await get_setting(session, "ui_theme") is None


async def test_delete_missing_returns_false(session: AsyncSession) -> None:
    assert await delete_setting(session, "ui_theme") is False


async def test_get_rejects_unknown_key(session: AsyncSession) -> None:
    with pytest.raises(UnknownSettingKeyError):
        await get_setting(session, "something_else")


async def test_set_rejects_unknown_key(session: AsyncSession) -> None:
    with pytest.raises(UnknownSettingKeyError):
        await set_setting(session, "llm_api_key", "sk-anything")


async def test_set_rejects_secret_looking_value(session: AsyncSession) -> None:
    # Even on an allow-listed key, scanning must block payloads that look like
    # secret material (the last_selected_provider_hint should be a provider name,
    # not a dict that contains an api_key).
    with pytest.raises(SecretPayloadRejectedError):
        await set_setting(
            session,
            "last_selected_provider_hint",
            {"provider": "openai", "api_key": "sk-leaked"},
        )


async def test_set_accepts_clean_provider_hint(session: AsyncSession) -> None:
    await set_setting(session, "last_selected_provider_hint", "siliconflow")

    assert await get_setting(session, "last_selected_provider_hint") == "siliconflow"
