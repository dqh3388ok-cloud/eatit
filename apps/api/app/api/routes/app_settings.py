"""app_settings REST routes.

Thin REST facade over `app.domain.settings.service`. Only whitelisted keys are
accepted (see `ALLOWED_KEYS` in the service). A separate secret-blocklist scan
prevents LLM credentials from slipping into the local key/value store even if
a buggy caller picks a whitelisted key.

Current consumers:
- Onboarding wizard persists `onboarding_completed_at` once step 4 finishes.
- OnboardingGate reads `onboarding_completed_at` to decide first-run redirect.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.settings.service import (
    SecretPayloadRejectedError,
    UnknownSettingKeyError,
    get_setting,
    set_setting,
)
from app.infra.db import get_async_session


router = APIRouter(prefix="/app-settings", tags=["app-settings"])


class AppSettingValue(BaseModel):
    value: Any


@router.get("/{key}", response_model=AppSettingValue)
async def read_app_setting(
    key: str,
    session: AsyncSession = Depends(get_async_session),
) -> AppSettingValue:
    try:
        value = await get_setting(session, key)
    except UnknownSettingKeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if value is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="not set")
    return AppSettingValue(value=value)


@router.put("/{key}", response_model=AppSettingValue)
async def write_app_setting(
    key: str,
    body: AppSettingValue,
    session: AsyncSession = Depends(get_async_session),
) -> AppSettingValue:
    try:
        await set_setting(session, key, body.value)
    except UnknownSettingKeyError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except SecretPayloadRejectedError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return AppSettingValue(value=body.value)
