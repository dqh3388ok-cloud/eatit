from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies.auth import AuthenticatedUser
from app.infra.db import AsyncSessionFactory
from app.infra.tasks import TaskQueueInterface
from app.models.enums import InterviewReportStatus, InterviewSessionStatus
from app.models.report import InterviewReport
from app.models.session import InterviewSession
from app.schemas.reports import (
    InterviewReportPayload,
    InterviewReportResponse,
    ReportStatusResponse,
    RoundReview,
    TriggerReportRequest,
    TriggerReportResponse,
)
from app.schemas.turns import NormalizedAnswer, NormalizedQuestion, NormalizedUserAssessment


class ReportsService:
    async def trigger_report(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        task_queue: TaskQueueInterface,
        session_id: UUID,
        request: TriggerReportRequest,
    ) -> TriggerReportResponse:
        interview_session = await self._get_owned_session(session, current_user, str(session_id))
        now = datetime.now(UTC)

        result = await session.execute(
            select(InterviewReport).where(InterviewReport.interview_session_id == interview_session.id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            report = InterviewReport(
                interview_session_id=interview_session.id,
                status=InterviewReportStatus.GENERATING,
                requested_at=now,
                generated_at=None,
                payload={},
            )
            session.add(report)
        elif request.force_regenerate or report.status != InterviewReportStatus.GENERATING:
            report.status = InterviewReportStatus.GENERATING
            report.requested_at = now
            report.generated_at = None
            report.payload = {}

        interview_session.status = InterviewSessionStatus.REPORT_GENERATING
        await session.commit()
        await task_queue.enqueue(
            task_name=f"generate-report:{interview_session.id}",
            task_factory=lambda: self._generate_report_task(interview_session.id),
        )

        return TriggerReportResponse(
            session_id=interview_session.id,
            status=InterviewReportStatus.GENERATING,
            requested_at=now,
        )

    async def get_report(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_id: UUID,
    ) -> InterviewReportResponse:
        interview_session = await self._get_owned_session(session, current_user, str(session_id))
        result = await session.execute(
            select(InterviewReport).where(InterviewReport.interview_session_id == interview_session.id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
        if report.status != InterviewReportStatus.READY or not report.payload:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Report is still generating.",
            )

        return InterviewReportResponse(
            id=report.id,
            created_at=report.created_at,
            updated_at=report.updated_at,
            interview_session_id=report.interview_session_id,
            status=report.status,
            requested_at=report.requested_at,
            generated_at=report.generated_at,
            payload=InterviewReportPayload.model_validate(report.payload),
        )

    async def get_report_status(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_id: UUID,
    ) -> ReportStatusResponse:
        interview_session = await self._get_owned_session(session, current_user, str(session_id))
        result = await session.execute(
            select(InterviewReport).where(InterviewReport.interview_session_id == interview_session.id)
        )
        report = result.scalar_one_or_none()
        if report is None:
            return ReportStatusResponse(
                session_id=interview_session.id,
                status=InterviewReportStatus.PENDING,
                has_payload=False,
            )
        return ReportStatusResponse(
            session_id=interview_session.id,
            status=report.status,
            has_payload=bool(report.payload),
        )

    async def _get_owned_session(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        session_id: str,
    ) -> InterviewSession:
        result = await session.execute(
            select(InterviewSession)
            .options(selectinload(InterviewSession.report))
            .where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == current_user.id,
            )
        )
        interview_session = result.scalar_one_or_none()
        if interview_session is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Session not found.")
        return interview_session

    async def _generate_report_task(self, session_id: str) -> None:
        async with AsyncSessionFactory() as session:
            result = await session.execute(
                select(InterviewSession).where(InterviewSession.id == session_id)
            )
            interview_session = result.scalar_one_or_none()
            if interview_session is None:
                return

            now = datetime.now(UTC)
            payload = self._mock_report_payload()
            result = await session.execute(
                select(InterviewReport).where(InterviewReport.interview_session_id == interview_session.id)
            )
            report = result.scalar_one_or_none()
            if report is None:
                report = InterviewReport(
                    interview_session_id=interview_session.id,
                    status=InterviewReportStatus.READY,
                    requested_at=now,
                    generated_at=now,
                    payload=payload.model_dump(mode="json"),
                )
                session.add(report)
            else:
                report.status = InterviewReportStatus.READY
                report.generated_at = now
                report.payload = payload.model_dump(mode="json")
                if report.requested_at is None:
                    report.requested_at = now

            interview_session.status = InterviewSessionStatus.REPORT_READY
            await session.commit()

    @staticmethod
    def _mock_report_payload() -> InterviewReportPayload:
        question = NormalizedQuestion(
            turn_index=1,
            stage_name="opening",
            question_tag="岗位匹配",
            question_text="请先做一个简短自我介绍，并说明你为什么适合这个岗位？",
        )
        answer = NormalizedAnswer(
            turn_index=1,
            transcript_text="我主要做过 AI 产品和增长实验平台，能把场景、指标和跨团队协作串起来。",
            cleaned_sentences=[
                "我主要做过 AI 产品。",
                "我也负责过增长实验平台。",
                "我能把场景、指标和跨团队协作串起来。",
            ],
            key_points=["AI 产品经验", "增长实验平台", "指标与协作"],
        )
        assessment = NormalizedUserAssessment(
            turn_index=1,
            strengths=["岗位相关度较高", "经历映射较直接"],
            weaknesses=["量化结果还不够具体"],
            risks=["容易停留在概括层"],
            suggestions=["补充关键指标", "补充主导动作"],
            evidence=["提到了 AI 产品和增长实验平台，但缺少具体结果数据。"],
        )
        return InterviewReportPayload(
            overall_summary="候选人整体方向匹配度较好，但需要进一步补齐量化结果和 ownership 证据。",
            round_reviews=[RoundReview(question=question, answer=answer, assessment=assessment)],
            strengths=["方向匹配度好", "表达结构清晰"],
            improvements=["补充量化结果", "增强项目 ownership 证明"],
            next_actions=["重新面试项目深挖方向", "准备 3 组关键指标案例"],
        )
