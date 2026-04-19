from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import AuthenticatedUser
from app.models.asset import CandidateAsset, ParseResult
from app.models.enums import (
    CandidateAssetStatus,
    InterviewSessionStatus,
)
from app.models.session import DirectionFramework, InterviewConfig, InterviewSession
from app.schemas.frameworks import DirectionFramework as DirectionFrameworkSchema
from app.schemas.frameworks import FrameworkStage
from app.schemas.parse import ParseResultPayload
from app.schemas.sessions import (
    CreateSessionRequest,
    CreateSessionResponse,
    EndSessionResponse,
    InterviewConfigResponse,
    SessionDetailResponse,
    SessionListRequest,
    SessionListResponse,
    SessionSummary,
)


class SessionsService:
    async def create_session(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        request: CreateSessionRequest,
    ) -> CreateSessionResponse:
        asset = await self._get_ready_asset(session, current_user, request.asset_bundle_id)
        parse_payload = await self._get_parse_payload(session, asset.id)
        framework = self._mock_direction_framework(request, parse_payload)

        interview_session = InterviewSession(
            user_id=current_user.id,
            candidate_asset_id=asset.id,
            status=InterviewSessionStatus.CREATED,
            config_snapshot=request.config.model_dump(mode="json"),
        )
        session.add(interview_session)
        await session.flush()

        session.add(
            InterviewConfig(
                interview_session_id=interview_session.id,
                style=request.config.style,
                direction=request.config.direction,
                duration_minutes=request.config.duration_minutes,
            )
        )
        session.add(
            DirectionFramework(
                interview_session_id=interview_session.id,
                payload=framework.model_dump(mode="json"),
            )
        )
        await session.commit()

        return CreateSessionResponse(
            session_id=interview_session.id,
            status=interview_session.status,
            direction_framework=framework,
        )

    async def get_session(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_id: UUID,
    ) -> SessionDetailResponse:
        interview_session = await self._get_owned_session(session, current_user, session_id)
        return self._serialize_session_detail(interview_session)

    async def list_sessions(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        query: SessionListRequest,
    ) -> SessionListResponse:
        filters = [InterviewSession.user_id == current_user.id]
        if query.status is not None:
            filters.append(InterviewSession.status == query.status)

        total = await session.scalar(select(func.count()).select_from(InterviewSession).where(*filters))
        result = await session.execute(
            select(InterviewSession)
            .where(*filters)
            .order_by(InterviewSession.created_at.desc())
            .offset((query.page - 1) * query.page_size)
            .limit(query.page_size)
        )
        items = [self._serialize_session_summary(item) for item in result.scalars().all()]
        return SessionListResponse(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=total or 0,
        )

    async def end_session(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_id: UUID,
    ) -> EndSessionResponse:
        interview_session = await self._get_owned_session(session, current_user, session_id)
        interview_session.status = InterviewSessionStatus.ENDED
        interview_session.ended_at = datetime.now(UTC)
        await session.commit()
        return EndSessionResponse(
            session_id=interview_session.id,
            status=interview_session.status,
            ended_at=interview_session.ended_at,
        )

    async def _get_ready_asset(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        asset_bundle_id: UUID,
    ) -> CandidateAsset:
        result = await session.execute(
            select(CandidateAsset).where(
                CandidateAsset.id == asset_bundle_id,
                CandidateAsset.user_id == current_user.id,
            )
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset bundle not found.")
        if asset.status != CandidateAssetStatus.ANALYSIS_READY:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Asset bundle must be parsed before creating a session.",
            )
        return asset

    async def _get_parse_payload(self, session: AsyncSession, asset_bundle_id: UUID) -> ParseResultPayload:
        result = await session.execute(
            select(ParseResult).where(ParseResult.candidate_asset_id == asset_bundle_id)
        )
        parse_result = result.scalar_one_or_none()
        if parse_result is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Parse result not found.")
        return ParseResultPayload.model_validate(parse_result.payload)

    async def _get_owned_session(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_id: UUID,
    ) -> InterviewSession:
        result = await session.execute(
            select(InterviewSession)
            .options(
                selectinload(InterviewSession.config),
                selectinload(InterviewSession.direction_framework),
            )
            .where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == current_user.id,
            )
        )
        interview_session = result.scalar_one_or_none()
        if interview_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return interview_session

    @staticmethod
    def _mock_direction_framework(
        request: CreateSessionRequest,
        parse_payload: ParseResultPayload,
    ) -> DirectionFrameworkSchema:
        focus_points = parse_payload.project_hooks[0].focus_points if parse_payload.project_hooks else ["岗位理解"]
        risk_points = [item.title for item in parse_payload.candidate_risks]
        return DirectionFrameworkSchema(
            style=request.config.style,
            direction=request.config.direction,
            duration_minutes=request.config.duration_minutes,
            stages=[
                FrameworkStage(name="opening", goal="自我介绍与岗位匹配", question_budget=2),
                FrameworkStage(name="core_project", goal="主项目背景/方案/结果/难点", question_budget=7),
                FrameworkStage(name="behavior", goal="协作/复盘/抗压", question_budget=3),
                FrameworkStage(name="closing", goal="候选人提问与总结", question_budget=1),
            ],
            focus_points=focus_points,
            risk_points=risk_points or ["回答跑偏", "数据不具体"],
        )

    @staticmethod
    def _serialize_session_summary(interview_session: InterviewSession) -> SessionSummary:
        return SessionSummary(
            id=interview_session.id,
            created_at=interview_session.created_at,
            updated_at=interview_session.updated_at,
            user_id=interview_session.user_id,
            candidate_asset_id=interview_session.candidate_asset_id,
            status=interview_session.status,
            started_at=interview_session.started_at,
            ended_at=interview_session.ended_at,
            turn_count=interview_session.turn_count,
            config_snapshot=interview_session.config_snapshot,
        )

    def _serialize_session_detail(self, interview_session: InterviewSession) -> SessionDetailResponse:
        config = None
        if interview_session.config is not None:
            config = InterviewConfigResponse(
                id=interview_session.config.id,
                created_at=interview_session.config.created_at,
                updated_at=interview_session.config.updated_at,
                interview_session_id=interview_session.config.interview_session_id,
                style=interview_session.config.style,
                direction=interview_session.config.direction,
                duration_minutes=interview_session.config.duration_minutes,
            )

        framework = None
        if interview_session.direction_framework is not None:
            framework = DirectionFrameworkSchema.model_validate(interview_session.direction_framework.payload)

        return SessionDetailResponse(
            **self._serialize_session_summary(interview_session).model_dump(),
            config=config,
            direction_framework=framework,
        )
