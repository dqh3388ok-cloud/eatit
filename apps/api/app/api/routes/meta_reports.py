from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedUser, get_current_user
from app.api.dependencies.llm import get_llm_config
from app.api.dependencies.tasks import get_task_queue
from app.domain.meta_reports.service import MetaReportsService
from app.infra.db import get_async_session
from app.infra.llm import LLMConfig
from app.infra.tasks import TaskQueueInterface
from app.schemas.meta_reports import (
    MetaReportDetailResponse,
    MetaReportListRequest,
    MetaReportListResponse,
    TriggerMetaReportRequest,
    TriggerMetaReportResponse,
)


router = APIRouter(prefix="/meta-reports", tags=["meta-reports"])
meta_reports_service = MetaReportsService()


@router.post("", response_model=TriggerMetaReportResponse, status_code=202)
async def trigger_meta_report(
    request: TriggerMetaReportRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
    task_queue: TaskQueueInterface = Depends(get_task_queue),
    llm_config: LLMConfig = Depends(get_llm_config),
) -> JSONResponse:
    payload = await meta_reports_service.trigger_meta_report(
        session, current_user, task_queue, request, llm_config
    )
    return JSONResponse(
        status_code=202,
        content=payload.model_dump(mode="json"),
    )


@router.get("/{meta_report_id}", response_model=MetaReportDetailResponse)
async def get_meta_report(
    meta_report_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> MetaReportDetailResponse:
    return await meta_reports_service.get_meta_report(session, current_user, meta_report_id)


@router.get("", response_model=MetaReportListResponse)
async def list_meta_reports(
    query: Annotated[MetaReportListRequest, Depends()],
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> MetaReportListResponse:
    return await meta_reports_service.list_meta_reports(session, current_user, query)
