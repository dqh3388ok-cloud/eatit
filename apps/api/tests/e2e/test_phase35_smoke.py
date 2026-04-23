"""Phase 3.5 end-to-end smoke tests.

Two integration-level guards for the 3.5 features:

1. MetaReport E2E — seed 3 finished sessions (each with a ready
   ReportAgent payload) directly in the DB, POST /meta-reports through
   the real REST router + real asyncio TaskQueue + real domain service,
   poll GET until ready, and assert the full MetaReportOutput shape
   shows up. Only MetaReportAgent is monkey-patched so the agent layer
   stays isolated while every layer above it is exercised.

2. Observer WS — drive the WebSocket flow (init + one turn.end) with
   every turn-graph agent patched and ObserverAgent patched to emit a
   known coaching line. Asserts that `server.coach.observation` appears
   in the drained events alongside the standard turn trio.
"""

from __future__ import annotations

import base64
import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import anyio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.api.dependencies.auth import (
    AuthenticatedUser,
    MOCK_USER_EMAIL,
    MOCK_USER_ID,
    get_websocket_user,
)
from app.infra.db import get_async_session
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
                "api_key": "sk-p35-smoke",
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
    import app.domain.meta_reports.service as meta_service_mod

    monkeypatch.setattr(meta_service_mod, "AsyncSessionFactory", sqlite_session_factory)

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_async_session, None)


async def _seed_three_finished_sessions(factory) -> list[str]:
    """Seed mock user + asset + 3 completed sessions with ready reports."""
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
        user_id, asset_id = user.id, asset.id

    t0 = datetime(2026, 4, 1, 9, 0, tzinfo=UTC)
    spec = [
        (t0, 50, "失败复盘"),
        (t0 + timedelta(days=7), 62, "指标设计"),
        (t0 + timedelta(days=14), 73, "指标设计"),
    ]
    session_ids: list[str] = []
    for created_at, pass_prob, aspect in spec:
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
                payload=_ready_report_payload(interview.id, pass_prob, aspect),
            )
            session.add(report)
            await session.commit()
            session_ids.append(interview.id)
    return session_ids


def _mock_meta_output(session_ids: list[str]) -> dict:
    return {
        "overall_trend_summary": (
            "你在最近三场面试里整体通过概率从 50 稳步提升到 73。"
            "指标设计已抵达 solid;失败复盘仍是反复出现的短板,"
            "建议下一轮系统补强。"
        ),
        "recurring_weaknesses": [
            {
                "aspect": "失败复盘",
                "occurrence_count": 3,
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
        "pass_probability_series": [
            {
                "session_id": session_ids[0],
                "session_created_at": "2026-04-01T09:00:00+00:00",
                "pass_probability": 50,
            },
            {
                "session_id": session_ids[1],
                "session_created_at": "2026-04-08T09:00:00+00:00",
                "pass_probability": 62,
            },
            {
                "session_id": session_ids[2],
                "session_created_at": "2026-04-15T09:00:00+00:00",
                "pass_probability": 73,
            },
        ],
        "next_focus_areas": [
            {
                "aspect": "失败复盘",
                "reason": "连续三场均落在 weak/mixed",
                "suggested_prep": "挑一个上季度失败项目,写 5 Whys 根因链",
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


async def test_phase35_meta_report_e2e_three_sessions(
    override_db, sqlite_session_factory, monkeypatch
) -> None:
    """3 mock sessions → POST /meta-reports → poll → assert shape."""
    session_ids = await _seed_three_finished_sessions(sqlite_session_factory)

    from app.agents.meta_report.schemas import MetaReportOutput
    from app.agents.meta_report.service import MetaReportAgentService

    expected_payload = _mock_meta_output(session_ids)

    async def fake_run(_self, input, _gateway):  # noqa: ANN001
        assert [s.session_id for s in input.sessions] == session_ids
        return MetaReportOutput.model_validate(expected_payload)

    monkeypatch.setattr(MetaReportAgentService, "run", fake_run)

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        trigger = await client.post("/api/v1/meta-reports", json={})
        assert trigger.status_code == 202
        trigger_body = trigger.json()
        assert trigger_body["covered_session_ids"] == session_ids
        meta_id = trigger_body["id"]

        ready: dict[str, Any] | None = None
        for _ in range(40):
            response = await client.get(f"/api/v1/meta-reports/{meta_id}")
            if response.status_code == 200:
                ready = response.json()
                break
            assert response.status_code == 409
            await anyio.sleep(0.05)

        # List endpoint picks up the new row too.
        listing = await client.get("/api/v1/meta-reports")
        assert listing.status_code == 200
        assert listing.json()["total"] == 1

    assert ready is not None, "meta report never transitioned to ready"
    assert ready["status"] == "ready"
    payload = ready["payload"]

    # Full shape assertions covering every top-level MetaReportOutput field.
    assert isinstance(payload["overall_trend_summary"], str)
    assert payload["overall_trend_summary"]
    assert len(payload["pass_probability_series"]) == 3
    assert [p["session_id"] for p in payload["pass_probability_series"]] == session_ids
    assert [p["pass_probability"] for p in payload["pass_probability_series"]] == [50, 62, 73]
    assert payload["recurring_weaknesses"][0]["occurrence_count"] == 3
    assert payload["recurring_weaknesses"][0]["aspect"] == "失败复盘"
    assert payload["improvement_signals"][0]["from_verdict"] == "weak"
    assert payload["improvement_signals"][0]["to_verdict"] == "solid"
    assert 3 <= len(payload["next_focus_areas"]) <= 5


# ---------------------------------------------------------------------------
# Observer WS smoke
# ---------------------------------------------------------------------------


class _FakeDBSession:
    """Minimal owner-check stub for the WS endpoint (see P3.12 e2e)."""

    def __init__(self, session_id: UUID) -> None:
        self._session_id = session_id
        self._calls = 0

    async def execute(self, *_args: Any, **_kwargs: Any) -> Any:
        self._calls += 1

        class _Result:
            def __init__(self, value: Any) -> None:
                self._value = value

            def scalar_one_or_none(self) -> Any:
                return self._value

        if self._calls == 1:
            return _Result(
                type(
                    "InterviewSessionStub",
                    (),
                    {"id": self._session_id, "user_id": MOCK_USER_ID},
                )()
            )
        return _Result(None)

    async def __aenter__(self) -> "_FakeDBSession":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None


def test_phase35_ws_emits_observer_event_in_turn_drain(monkeypatch) -> None:
    """Single turn.end → drained events include server.coach.observation."""
    from app.agents.compression.schemas import CompressionAgentOutput
    from app.agents.compression.service import CompressionAgentService
    from app.agents.interviewer.schemas import InterviewerAgentOutput
    from app.agents.interviewer.service import InterviewerAgentService
    from app.agents.observer.schemas import ObserverAgentOutput
    from app.agents.observer.service import ObserverAgentService
    from app.agents.reference.schemas import ReferenceAgentOutput
    from app.agents.reference.service import ReferenceAgentService
    from app.orchestrator import turn_graph as turn_graph_mod
    from app.orchestrator.state import TurnAssessment
    from app.ws import endpoint as ws_endpoint

    session_uuid = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f000a7")

    async def fake_interviewer_run(_self, _input, _gateway):
        return InterviewerAgentOutput(
            question="请先介绍一下你最近一个完整上线的项目。",
            intent="暖场",
            expected_depth="surface",
            followup_hint=None,
            should_end=False,
        )

    async def fake_compression_run(_self, _input, _gateway):
        return CompressionAgentOutput(
            summary="候选人围绕一个 LLM 产品项目展开。",
            preserved_keywords=["北极星指标"],
            open_threads=[],
        )

    async def fake_reference_run(_self, _input, _gateway):
        return ReferenceAgentOutput(
            answer_outline=["先锁用户价值"],
            ideal_answer="参考答案略。",
            key_evaluation_points=["能否归因"],
            common_pitfalls=["一上来就用 DAU"],
        )

    async def fake_observer_run(_self, _input, _gateway):
        return ObserverAgentOutput(
            observation="你这段量化很到位,保持节奏",
            tone="support",
            actionable=False,
        )

    async def fake_structured_completion(
        _client, *, messages, response_model, max_retries=2
    ):  # noqa: ANN001
        if response_model is TurnAssessment:
            return TurnAssessment(
                summary="结构清晰",
                strengths=["量化到位"],
                weaknesses=[],
            )
        raise AssertionError(f"unexpected response_model: {response_model}")

    monkeypatch.setattr(InterviewerAgentService, "run", fake_interviewer_run)
    monkeypatch.setattr(CompressionAgentService, "run", fake_compression_run)
    monkeypatch.setattr(ReferenceAgentService, "run", fake_reference_run)
    monkeypatch.setattr(ObserverAgentService, "run", fake_observer_run)
    monkeypatch.setattr(turn_graph_mod, "structured_completion", fake_structured_completion)

    monkeypatch.setattr(
        ws_endpoint,
        "AsyncSessionFactory",
        lambda: _FakeDBSession(session_uuid),
    )

    async def fake_get_ws_user(*_args: Any, **_kwargs: Any) -> AuthenticatedUser:
        return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)

    monkeypatch.setattr(ws_endpoint, "get_websocket_user", fake_get_ws_user)
    app.dependency_overrides[get_websocket_user] = fake_get_ws_user

    try:
        with TestClient(app) as client:
            with client.websocket_connect(
                f"/ws/sessions/{session_uuid}?token=mock"
            ) as ws:
                ws.send_json(
                    {
                        "event": "client.session.init",
                        "config": {
                            "provider": "openai",
                            "api_key": "sk-p35-ws",
                            "model": "gpt-4o-mini",
                            "base_url": None,
                        },
                    }
                )
                ws.send_json(
                    {
                        "event": "client.turn.end",
                        "turn_index": 1,
                        "question": "请先介绍一下你最近一个完整上线的项目。",
                        "answer": "我们用完成率作为北极星指标,从 42% 拉到 58%。",
                    }
                )

                # Drain up to 8 events so the fire-and-forget observer +
                # reference tasks have a chance to land after the core trio.
                events: list[dict] = []
                want = {
                    "server.turn.assessed",
                    "server.turn.compressed",
                    "server.question.generated",
                    "server.coach.observation",
                }
                seen: set[str] = set()
                for _ in range(8):
                    event = ws.receive_json()
                    events.append(event)
                    seen.add(event["event"])
                    if want.issubset(seen):
                        break

                ws.send_json({"event": "client.session.end"})
    finally:
        app.dependency_overrides.pop(get_websocket_user, None)

    assert "server.coach.observation" in seen, (
        f"observer event missing from drain: {[e['event'] for e in events]}"
    )
    coach_event = next(e for e in events if e["event"] == "server.coach.observation")
    assert coach_event["payload"]["turn_index"] == 1
    assert coach_event["payload"]["tone"] == "support"
    assert coach_event["payload"]["actionable"] is False
    assert coach_event["payload"]["observation"] == "你这段量化很到位,保持节奏"
    assert len(coach_event["payload"]["observation"]) <= 60
