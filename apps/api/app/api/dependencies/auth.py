from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infra.db import get_async_session
from app.models.user import User
from fastapi import Depends


MOCK_USER_ID = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00001")
MOCK_USER_EMAIL = "mock-user@eatit.local"


class AuthenticatedUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: str


async def ensure_mock_user(session: AsyncSession) -> AuthenticatedUser:
    result = await session.execute(select(User).where(User.id == MOCK_USER_ID))
    user = result.scalar_one_or_none()

    if user is None:
        user = User(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)
        session.add(user)
        await session.commit()
        await session.refresh(user)

    return AuthenticatedUser.model_validate(user)


async def get_current_user(
    session: AsyncSession = Depends(get_async_session),
) -> AuthenticatedUser:
    return await ensure_mock_user(session)


async def get_websocket_user(
    token: str,
    session: AsyncSession,
) -> AuthenticatedUser:
    if not token.strip():
        raise ValueError("Missing websocket token.")
    return await ensure_mock_user(session)
