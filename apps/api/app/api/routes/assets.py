from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedUser, get_current_user
from app.domain.assets.service import AssetsService
from app.infra.db import get_async_session
from app.schemas.assets import AssetUploadRequest, AssetUploadResponse
from app.schemas.parse import ParseRequestResponse, ParseResultResponse


router = APIRouter(prefix="/assets", tags=["assets"])
service = AssetsService()


@router.post("/resume", response_model=AssetUploadResponse)
async def upload_resume(
    request: Annotated[AssetUploadRequest, Form()],
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AssetUploadResponse:
    return await service.upload_resume(session, current_user, file, request.asset_bundle_id)


@router.post("/jd", response_model=AssetUploadResponse)
async def upload_jd(
    request: Annotated[AssetUploadRequest, Form()],
    file: UploadFile = File(...),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> AssetUploadResponse:
    return await service.upload_jd(session, current_user, file, request.asset_bundle_id)


@router.post("/{asset_bundle_id}/parse", response_model=ParseRequestResponse)
async def trigger_parse(
    asset_bundle_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ParseRequestResponse:
    return await service.trigger_parse(session, current_user, asset_bundle_id)


@router.get("/{asset_bundle_id}/parse", response_model=ParseResultResponse)
async def get_parse_result(
    asset_bundle_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> ParseResultResponse:
    return await service.get_parse_result(session, current_user, asset_bundle_id)
