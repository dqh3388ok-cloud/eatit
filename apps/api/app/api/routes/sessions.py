from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Body, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import AuthenticatedUser, get_current_user
from app.api.dependencies.llm import get_llm_config, get_llm_gateway
from app.api.dependencies.tasks import get_task_queue
from app.domain.reports.service import ReportsService
from app.domain.sessions.service import SessionsService
from app.infra.db import get_async_session
from app.infra.llm import LLMConfig, LLMGateway
from app.infra.tasks import TaskQueueInterface
from app.schemas.reports import InterviewReportResponse, TriggerReportRequest, TriggerReportResponse
from app.schemas.sessions import (
    CreateSessionRequest,
    CreateSessionResponse,
    EndSessionResponse,
    SessionDetailResponse,
    SessionListRequest,
    SessionListResponse,
)


router = APIRouter(prefix="/sessions", tags=["sessions"])
sessions_service = SessionsService()
reports_service = ReportsService()


@router.post("", response_model=CreateSessionResponse)
async def create_session(
    request: CreateSessionRequest,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> CreateSessionResponse:
    return await sessions_service.create_session(session, current_user, request, gateway)


@router.get("/{session_id}", response_model=SessionDetailResponse)
async def get_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SessionDetailResponse:
    return await sessions_service.get_session(session, current_user, session_id)


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    query: Annotated[SessionListRequest, Depends()],
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> SessionListResponse:
    return await sessions_service.list_sessions(session, current_user, query)


@router.post("/{session_id}/end", response_model=EndSessionResponse)
async def end_session(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> EndSessionResponse:
    return await sessions_service.end_session(session, current_user, session_id)


@router.post("/{session_id}/report", response_model=TriggerReportResponse)
async def trigger_report(
    session_id: UUID,
    request: TriggerReportRequest = Body(default_factory=TriggerReportRequest),
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
    task_queue: TaskQueueInterface = Depends(get_task_queue),
    llm_config: LLMConfig = Depends(get_llm_config),
) -> TriggerReportResponse:
    return await reports_service.trigger_report(
        session,
        current_user,
        task_queue,
        session_id,
        request,
        llm_config,
    )


@router.get("/{session_id}/report", response_model=InterviewReportResponse)
async def get_report(
    session_id: UUID,
    current_user: AuthenticatedUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_session),
) -> InterviewReportResponse:
    return await reports_service.get_report(session, current_user, session_id)
