from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.meta_report.schemas import (
    MetaReportAgentInput,
    MetaReportSessionInput,
)
from app.agents.meta_report.service import MetaReportAgentService
from app.api.dependencies.auth import AuthenticatedUser
from app.infra.db import AsyncSessionFactory
from app.infra.llm import LLMConfig, build_gateway
from app.infra.llm.errors import LLMError
from app.infra.tasks import TaskQueueInterface
from app.models.enums import InterviewReportStatus, MetaReportStatus
from app.models.meta_report import MetaReport
from app.models.report import InterviewReport
from app.models.session import InterviewSession
from app.schemas.meta_reports import (
    MetaReportDetailResponse,
    MetaReportListItem,
    MetaReportListRequest,
    MetaReportListResponse,
    TriggerMetaReportRequest,
    TriggerMetaReportResponse,
)

_EMPTY_REPORTS_DETAIL = "至少需要 1 场已完成的面试"


class MetaReportsService:
    async def trigger_meta_report(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        task_queue: TaskQueueInterface,
        request: TriggerMetaReportRequest,
        llm_config: LLMConfig,
    ) -> TriggerMetaReportResponse:
        eligible = await self._load_eligible_sessions(
            session, current_user, request.session_ids
        )
        if not eligible:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=_EMPTY_REPORTS_DETAIL,
            )

        covered_session_ids = [s.id for s in eligible]
        meta_report = MetaReport(
            user_id=current_user.id,
            covered_session_ids=covered_session_ids,
            status=MetaReportStatus.GENERATING,
            payload=None,
        )
        session.add(meta_report)
        await session.commit()
        await session.refresh(meta_report)

        meta_report_id = meta_report.id
        task_id = await task_queue.enqueue(
            task_name=f"generate-meta-report:{meta_report_id}",
            task_factory=lambda: self._generate_meta_report_task(
                meta_report_id, covered_session_ids, llm_config
            ),
        )

        return TriggerMetaReportResponse(
            id=meta_report.id,
            task_id=task_id,
            status=MetaReportStatus.GENERATING,
            covered_session_ids=covered_session_ids,
            created_at=meta_report.created_at,
        )

    async def get_meta_report(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        meta_report_id: UUID,
    ) -> MetaReportDetailResponse:
        meta_report = await self._get_owned(session, current_user, str(meta_report_id))
        if meta_report.status == MetaReportStatus.GENERATING:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Meta report is still generating.",
            )
        return MetaReportDetailResponse(
            id=meta_report.id,
            user_id=meta_report.user_id,
            status=meta_report.status,
            covered_session_ids=list(meta_report.covered_session_ids or []),
            payload=meta_report.payload,
            created_at=meta_report.created_at,
            updated_at=meta_report.updated_at,
        )

    async def list_meta_reports(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        query: MetaReportListRequest,
    ) -> MetaReportListResponse:
        offset = (query.page - 1) * query.page_size

        total_result = await session.execute(
            select(func.count())
            .select_from(MetaReport)
            .where(MetaReport.user_id == current_user.id)
        )
        total = int(total_result.scalar_one() or 0)

        rows_result = await session.execute(
            select(MetaReport)
            .where(MetaReport.user_id == current_user.id)
            .order_by(MetaReport.created_at.desc())
            .offset(offset)
            .limit(query.page_size)
        )
        rows = rows_result.scalars().all()

        items = [
            MetaReportListItem(
                id=row.id,
                status=row.status,
                covered_session_ids=list(row.covered_session_ids or []),
                session_count=len(row.covered_session_ids or []),
                created_at=row.created_at,
            )
            for row in rows
        ]

        return MetaReportListResponse(
            items=items,
            page=query.page,
            page_size=query.page_size,
            total=total,
        )

    async def _get_owned(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        meta_report_id: str,
    ) -> MetaReport:
        result = await session.execute(
            select(MetaReport).where(
                MetaReport.id == meta_report_id,
                MetaReport.user_id == current_user.id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Meta report not found.",
            )
        return row

    async def _load_eligible_sessions(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_ids: list[str] | None,
    ) -> list[InterviewSession]:
        """Return sessions belonging to the user that have a ready report.

        Ordered by session.created_at ascending so the agent's trend logic
        can assume chronological order without re-sorting.
        """
        stmt = (
            select(InterviewSession)
            .join(InterviewReport, InterviewReport.interview_session_id == InterviewSession.id)
            .where(
                InterviewSession.user_id == current_user.id,
                InterviewReport.status == InterviewReportStatus.READY,
            )
            .order_by(InterviewSession.created_at.asc())
        )
        if session_ids:
            stmt = stmt.where(InterviewSession.id.in_(session_ids))

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def _generate_meta_report_task(
        self,
        meta_report_id: str,
        session_ids: list[str],
        llm_config: LLMConfig,
    ) -> None:
        async with AsyncSessionFactory() as session:
            sessions_input = await self._build_agent_input(session, session_ids)

            try:
                agent_output = await MetaReportAgentService().run(
                    sessions_input, build_gateway(llm_config)
                )
            except LLMError as exc:
                await self._mark_failed(session, meta_report_id, str(exc))
                return
            except Exception as exc:  # defensive: unknown provider issue
                await self._mark_failed(session, meta_report_id, f"{type(exc).__name__}: {exc}")
                raise

            result = await session.execute(
                select(MetaReport).where(MetaReport.id == meta_report_id)
            )
            meta_report = result.scalar_one_or_none()
            if meta_report is None:
                return
            meta_report.status = MetaReportStatus.READY
            meta_report.payload = agent_output.model_dump(mode="json")
            await session.commit()

    @staticmethod
    async def _build_agent_input(
        session: AsyncSession, session_ids: list[str]
    ) -> MetaReportAgentInput:
        result = await session.execute(
            select(InterviewSession, InterviewReport)
            .join(InterviewReport, InterviewReport.interview_session_id == InterviewSession.id)
            .where(InterviewSession.id.in_(session_ids))
            .order_by(InterviewSession.created_at.asc())
        )
        pairs = result.all()
        agent_sessions = [
            MetaReportSessionInput(
                session_id=interview_session.id,
                session_created_at=interview_session.created_at,
                config_snapshot=dict(interview_session.config_snapshot or {}),
                report_payload=dict(report.payload or {}),
            )
            for interview_session, report in pairs
        ]
        return MetaReportAgentInput(sessions=agent_sessions)

    @staticmethod
    async def _mark_failed(
        session: AsyncSession, meta_report_id: str, detail: str
    ) -> None:
        result = await session.execute(
            select(MetaReport).where(MetaReport.id == meta_report_id)
        )
        meta_report = result.scalar_one_or_none()
        if meta_report is None:
            return
        meta_report.status = MetaReportStatus.FAILED
        meta_report.payload = {"detail": detail}
        await session.commit()
