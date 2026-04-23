from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta

import anyio
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.dependencies.auth import MOCK_USER_EMAIL, MOCK_USER_ID
from app.infra.db import get_async_session
from app.infra.llm.errors import LLMNetworkError
from app.main import app
from app.models import (
    Base,
    CandidateAsset,
    InterviewReport,
    InterviewSession,
    User,
)
from app.models.enums import (
    CandidateAssetStatus,
    InterviewReportStatus,
    InterviewSessionStatus,
)


def _llm_config_header() -> str:
    return base64.b64encode(
        json.dumps(
            {
                "provider": "openai",
                "api_key": "sk-meta-wire",
                "model": "gpt-4o-mini",
                "base_url": None,
            }
        ).encode("utf-8")
    ).decode("ascii")


def _ready_report_payload(
    session_id: str, pass_probability: int, aspect: str
) -> dict:
    return {
        "overall_summary": f"session {session_id} summary",
        "round_reviews": [],
        "strengths": [aspect] if pass_probability >= 60 else [],
        "improvements": [aspect] if pass_probability < 60 else [],
        "next_actions": ["整理上线项目的指标体系表"],
        "pass_probability": pass_probability,
        "reasons": [
            {
                "aspect": aspect,
                "verdict": "solid" if pass_probability >= 60 else "weak",
                "evidence_turn_index": 0,
                "quote": f"quote about {aspect}",
            }
        ],
    }


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
def override_db(sqlite_session_factory, monkeypatch):
    async def _override() -> AsyncIterator[AsyncSession]:
        async with sqlite_session_factory() as s:
            yield s

    app.dependency_overrides[get_async_session] = _override
    # The background task re-opens a fresh session via AsyncSessionFactory;
    # point that at the same in-memory engine so the task sees the seeded rows.
    import app.domain.meta_reports.service as meta_service_mod

    monkeypatch.setattr(meta_service_mod, "AsyncSessionFactory", sqlite_session_factory)

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_async_session, None)


async def _seed_user_and_asset(factory) -> tuple[str, str]:
    async with factory() as session:
        user = User(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)
        session.add(user)
        asset = CandidateAsset(
            user_id=user.id,
            resume_file_ref=None,
            resume_filename="r.txt",
            resume_content_type="text/plain",
            jd_file_ref=None,
            jd_filename="j.txt",
            jd_content_type="text/plain",
            status=CandidateAssetStatus.ANALYSIS_READY,
        )
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
        return user.id, asset.id


async def _seed_session_with_ready_report(
    factory,
    user_id: str,
    asset_id: str,
    created_at: datetime,
    pass_probability: int,
    aspect: str,
) -> str:
    async with factory() as session:
        interview = InterviewSession(
            user_id=user_id,
            candidate_asset_id=asset_id,
            status=InterviewSessionStatus.REPORT_READY,
            started_at=created_at,
            ended_at=created_at,
            turn_count=3,
            config_snapshot={
                "style": "standard_professional",
                "direction": "project_deep_dive",
                "duration_minutes": 20,
            },
            created_at=created_at,
            updated_at=created_at,
        )
        session.add(interview)
        await session.flush()
        report = InterviewReport(
            interview_session_id=interview.id,
            status=InterviewReportStatus.READY,
            requested_at=created_at,
            generated_at=created_at,
            payload=_ready_report_payload(interview.id, pass_probability, aspect),
        )
        session.add(report)
        await session.commit()
        return interview.id


def _fake_agent_payload(session_ids: list[str], covered_count: int) -> dict:
    base_prob = 55
    series = [
        {
            "session_id": sid,
            "session_created_at": "2026-04-01T09:00:00+00:00",
            "pass_probability": base_prob + idx * 5,
        }
        for idx, sid in enumerate(session_ids)
    ]
    if covered_count == 1:
        return {
            "overall_trend_summary": (
                "这一场你的整体通过概率落在 55,指标设计维度评为 mixed。"
                "先补 counter metric 的讨论再考虑其他方向。本场唯一的明确短板集中在这里。"
            ),
            "recurring_weaknesses": [],
            "improvement_signals": [],
            "pass_probability_series": series,
            "next_focus_areas": [
                {
                    "aspect": "指标设计",
                    "reason": "本场 verdict 为 mixed",
                    "suggested_prep": "写清楚北极星 + 反指标",
                },
                {
                    "aspect": "量化证据",
                    "reason": "本场作答未给具体数字",
                    "suggested_prep": "把最近两个项目结果量化到三位有效数字",
                },
                {
                    "aspect": "失败复盘",
                    "reason": "尚未覆盖",
                    "suggested_prep": "准备一段 5 Whys 形式的失败复盘",
                },
            ],
        }
    return {
        "overall_trend_summary": (
            "你在最近几次面试里整体通过概率稳步提升。指标设计已抵达 solid;"
            "失败复盘仍是反复出现的短板,建议下一轮系统补强。"
        ),
        "recurring_weaknesses": [
            {
                "aspect": "失败复盘",
                "occurrence_count": len(session_ids),
                "session_ids": list(session_ids),
                "evidence_quotes": ["quote about 失败复盘"],
            }
        ],
        "improvement_signals": [
            {
                "aspect": "指标设计",
                "from_verdict": "weak",
                "to_verdict": "solid",
                "earlier_session_id": session_ids[0],
                "later_session_id": session_ids[-1],
            }
        ],
        "pass_probability_series": series,
        "next_focus_areas": [
            {
                "aspect": "失败复盘",
                "reason": "连续多场 weak",
                "suggested_prep": "写 5 Whys 根因链并量化损失",
            },
            {
                "aspect": "跨团队协作",
                "reason": "最近两场未主动举例",
                "suggested_prep": "准备一段跨三个团队交付的具体案例",
            },
            {
                "aspect": "指标设计",
                "reason": "已稳住 solid,counter metric 未讨论",
                "suggested_prep": "设计一组北极星 + 反指标配对",
            },
        ],
    }


def _patch_agent_to_return_payload(monkeypatch, covered_count: int) -> None:
    from app.agents.meta_report.schemas import MetaReportOutput
    from app.agents.meta_report.service import MetaReportAgentService

    async def _fake_run(self, input, gateway):  # noqa: ANN001
        ids = [s.session_id for s in input.sessions]
        return MetaReportOutput.model_validate(_fake_agent_payload(ids, covered_count))

    monkeypatch.setattr(MetaReportAgentService, "run", _fake_run)


def _patch_agent_to_raise(monkeypatch, exc: Exception) -> None:
    from app.agents.meta_report.service import MetaReportAgentService

    async def _fake_run(self, input, gateway):  # noqa: ANN001
        raise exc

    monkeypatch.setattr(MetaReportAgentService, "run", _fake_run)


async def _poll_until_not_409(client: AsyncClient, meta_report_id: str, tries: int = 40):
    for _ in range(tries):
        response = await client.get(f"/api/v1/meta-reports/{meta_report_id}")
        if response.status_code != 409:
            return response
        await anyio.sleep(0.05)
    raise AssertionError("Meta report never left generating state.")


async def test_trigger_with_zero_ready_reports_returns_400(
    override_db, sqlite_session_factory
) -> None:
    user_id, asset_id = await _seed_user_and_asset(sqlite_session_factory)
    # Seed a session but without a ready report — it must not count.
    async with sqlite_session_factory() as session:
        now = datetime.now(UTC)
        interview = InterviewSession(
            user_id=user_id,
            candidate_asset_id=asset_id,
            status=InterviewSessionStatus.ENDED,
            turn_count=0,
            config_snapshot={},
            created_at=now,
            updated_at=now,
        )
        session.add(interview)
        await session.commit()

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        response = await client.post("/api/v1/meta-reports", json={})

    assert response.status_code == 400
    assert response.json()["detail"] == "至少需要 1 场已完成的面试"


async def test_trigger_single_report_takes_retrospective_path(
    override_db, sqlite_session_factory, monkeypatch
) -> None:
    user_id, asset_id = await _seed_user_and_asset(sqlite_session_factory)
    session_id = await _seed_session_with_ready_report(
        sqlite_session_factory,
        user_id,
        asset_id,
        datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        pass_probability=58,
        aspect="指标设计",
    )
    _patch_agent_to_return_payload(monkeypatch, covered_count=1)

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        response = await client.post("/api/v1/meta-reports", json={})
        assert response.status_code == 202
        body = response.json()
        assert body["status"] == "generating"
        assert body["covered_session_ids"] == [session_id]
        meta_id = body["id"]

        ready = await _poll_until_not_409(client, meta_id)

    assert ready.status_code == 200
    payload = ready.json()["payload"]
    assert payload["recurring_weaknesses"] == []
    assert payload["improvement_signals"] == []
    assert len(payload["pass_probability_series"]) == 1
    assert payload["pass_probability_series"][0]["session_id"] == session_id
    assert "几次面试" not in payload["overall_trend_summary"]


async def test_trigger_multiple_reports_takes_cross_session_path(
    override_db, sqlite_session_factory, monkeypatch
) -> None:
    user_id, asset_id = await _seed_user_and_asset(sqlite_session_factory)
    t0 = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
    sid_a = await _seed_session_with_ready_report(
        sqlite_session_factory, user_id, asset_id, t0, 50, "失败复盘"
    )
    sid_b = await _seed_session_with_ready_report(
        sqlite_session_factory, user_id, asset_id, t0 + timedelta(days=7), 65, "指标设计"
    )
    sid_c = await _seed_session_with_ready_report(
        sqlite_session_factory, user_id, asset_id, t0 + timedelta(days=14), 72, "指标设计"
    )
    _patch_agent_to_return_payload(monkeypatch, covered_count=3)

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        response = await client.post("/api/v1/meta-reports", json={})
        assert response.status_code == 202
        body = response.json()
        assert body["covered_session_ids"] == [sid_a, sid_b, sid_c]
        meta_id = body["id"]

        ready = await _poll_until_not_409(client, meta_id)

    assert ready.status_code == 200
    payload = ready.json()["payload"]
    assert len(payload["pass_probability_series"]) == 3
    assert payload["recurring_weaknesses"][0]["occurrence_count"] == 3
    assert payload["improvement_signals"][0]["from_verdict"] == "weak"


async def test_get_while_in_flight_returns_409(
    override_db, sqlite_session_factory, monkeypatch
) -> None:
    user_id, asset_id = await _seed_user_and_asset(sqlite_session_factory)
    await _seed_session_with_ready_report(
        sqlite_session_factory,
        user_id,
        asset_id,
        datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        58,
        "指标设计",
    )

    # Agent blocks forever so the background task never completes.
    blocked = anyio.Event()

    from app.agents.meta_report.service import MetaReportAgentService

    async def _blocked_run(self, input, gateway):  # noqa: ANN001
        await blocked.wait()  # pragma: no cover (event never set in test)

    monkeypatch.setattr(MetaReportAgentService, "run", _blocked_run)

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=headers
        ) as client:
            trigger = await client.post("/api/v1/meta-reports", json={})
            assert trigger.status_code == 202
            meta_id = trigger.json()["id"]

            response = await client.get(f"/api/v1/meta-reports/{meta_id}")

        assert response.status_code == 409
    finally:
        blocked.set()


async def test_list_meta_reports_returns_paginated_history(
    override_db, sqlite_session_factory, monkeypatch
) -> None:
    user_id, asset_id = await _seed_user_and_asset(sqlite_session_factory)
    await _seed_session_with_ready_report(
        sqlite_session_factory,
        user_id,
        asset_id,
        datetime(2026, 4, 10, 9, 0, tzinfo=UTC),
        60,
        "指标设计",
    )
    _patch_agent_to_return_payload(monkeypatch, covered_count=1)

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        trigger = await client.post("/api/v1/meta-reports", json={})
        assert trigger.status_code == 202
        meta_id = trigger.json()["id"]
        await _poll_until_not_409(client, meta_id)

        listing = await client.get("/api/v1/meta-reports", params={"page": 1, "page_size": 10})

    assert listing.status_code == 200
    data = listing.json()
    assert data["total"] == 1
    assert data["items"][0]["id"] == meta_id
    assert data["items"][0]["session_count"] == 1
    assert data["items"][0]["status"] == "ready"


async def test_agent_llm_error_marks_failed_and_serves_200(
    override_db, sqlite_session_factory, monkeypatch
) -> None:
    user_id, asset_id = await _seed_user_and_asset(sqlite_session_factory)
    await _seed_session_with_ready_report(
        sqlite_session_factory,
        user_id,
        asset_id,
        datetime(2026, 4, 20, 9, 0, tzinfo=UTC),
        58,
        "指标设计",
    )
    _patch_agent_to_raise(monkeypatch, LLMNetworkError("upstream down"))

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        trigger = await client.post("/api/v1/meta-reports", json={})
        assert trigger.status_code == 202
        meta_id = trigger.json()["id"]

        ready = await _poll_until_not_409(client, meta_id)

    assert ready.status_code == 200
    body = ready.json()
    assert body["status"] == "failed"
    assert body["payload"] == {"detail": "upstream down"}
