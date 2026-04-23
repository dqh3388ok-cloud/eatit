"""Phase 3 end-to-end smoke test.

Drives the full flow with an in-process mock gateway:

    upload resume + JD
      -> POST /parse
      -> POST /sessions
      -> WS connect + client.session.init
      -> 3 × client.turn.end (with assessment/compression/next-question
         events drained in between)
      -> POST /report
      -> GET /report polled until ready
      -> assert every A4 field (pass_probability / reasons /
         next_actions) is present and well-formed.

Every agent's `run` method is monkey-patched at the class level so the
real service + DB + task queue + WS handler + SessionRuntime are all
exercised; only the LLM calls are stubbed. The inline `turn_assessment`
node lives in `app.orchestrator.turn_graph.structured_completion`, so we
patch that symbol too.
"""

from __future__ import annotations

import base64
import json
import time
from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from app.agents.compression.schemas import CompressionAgentOutput
from app.agents.framework.schemas import (
    DeepDiveAnchor,
    FocusCompetency,
    FrameworkAgentOutput,
    PacePlan,
    PaceSegment,
)
from app.agents.interviewer.schemas import InterviewerAgentOutput
from app.agents.parse.schemas import ParseAgentOutput
from app.agents.reference.schemas import ReferenceAgentOutput
from app.agents.report.schemas import Reason, ReportAgentOutput
from app.api.dependencies.auth import (
    AuthenticatedUser,
    MOCK_USER_EMAIL,
    MOCK_USER_ID,
    get_websocket_user,
)
from app.main import app
from app.orchestrator.state import TurnAssessment


def _llm_config_header() -> str:
    return base64.b64encode(
        json.dumps(
            {
                "provider": "openai",
                "api_key": "sk-e2e-test",
                "model": "gpt-4o-mini",
                "base_url": None,
            }
        ).encode("utf-8")
    ).decode("ascii")


def _parse_payload() -> ParseAgentOutput:
    return ParseAgentOutput.model_validate(
        {
            "job_requirements": [{"title": "AI 产品能力", "detail": "能把模型能力落到用户场景"}],
            "candidate_highlights": [{"title": "项目结果", "detail": "有量化指标的上线经验"}],
            "candidate_risks": [{"title": "跨团队协作", "detail": "多线配合的例子偏少"}],
            "project_hooks": [
                {
                    "project_name": "AI 面试官",
                    "reason": "与岗位 AI 能力高度相关",
                    "focus_points": ["场景选择", "指标设计"],
                }
            ],
            "match_summary": "整体匹配度良好,量化与协作需要补强。",
        }
    )


def _framework_payload() -> FrameworkAgentOutput:
    return FrameworkAgentOutput(
        direction="project_deep_dive",
        focus_competencies=[
            FocusCompetency(title="指标设计", why="AI PM 核心", probe_hint="0→1 项目"),
            FocusCompetency(title="跨团队推动", why="岗位描述核心", probe_hint="多线配合细节"),
        ],
        opening_questions=["请先介绍一下你最近一个完整上线的 AI 产品项目。"],
        deep_dive_anchors=[
            DeepDiveAnchor(anchor="AI 面试官", probe_chain=["what", "why", "how", "what-if"]),
        ],
        pace_plan=PacePlan(
            total_minutes=20,
            segments=[
                PaceSegment(name="opening", rough_minutes=3, goal="破冰"),
                PaceSegment(name="core_project", rough_minutes=12, goal="项目深挖"),
                PaceSegment(name="closing", rough_minutes=5, goal="反问"),
            ],
        ),
    )


def _interviewer_payload(turn_index: int) -> InterviewerAgentOutput:
    return InterviewerAgentOutput(
        question=f"针对第 {turn_index + 1} 轮,你当时是如何决定这个指标的?",
        intent="深入指标设计链路",
        expected_depth="tactical",
        followup_hint=None,
        should_end=False,
    )


def _compression_payload() -> CompressionAgentOutput:
    return CompressionAgentOutput(
        summary="候选人围绕一个 LLM 产品项目展开,指标环节比较清晰。",
        preserved_keywords=["北极星指标", "A/B 框架"],
        open_threads=["counter metric 还没问过"],
    )


def _reference_payload() -> ReferenceAgentOutput:
    return ReferenceAgentOutput(
        answer_outline=["先锁用户价值", "再拆中间量"],
        ideal_answer="参考答案略。",
        key_evaluation_points=["是否能归因到模型改动"],
        common_pitfalls=["一上来就用 DAU"],
    )


def _report_payload() -> ReportAgentOutput:
    return ReportAgentOutput(
        pass_probability=74,
        summary="候选人整体胜任,指标设计清晰,协作例子略薄。",
        reasons=[
            Reason(
                aspect="指标设计",
                verdict="solid",
                evidence_turn_index=0,
                quote="完成率作为北极星指标",
            ),
            Reason(
                aspect="跨团队协作",
                verdict="mixed",
                evidence_turn_index=1,
                quote="主要是配合设计师评审",
            ),
            Reason(
                aspect="失败复盘",
                verdict="weak",
                evidence_turn_index=2,
                quote="那次项目我没有深度参与复盘",
            ),
        ],
        next_actions=[
            "整理上线指标与 counter metric 对照表",
            "准备跨团队协作中一个主动推动的例子",
            "复盘最近一次失败项目的根因",
        ],
    )


class _FakeDBSession:
    """Stand-in for the WS endpoint's owner-check DB session.

    Returns a matching InterviewSession on the first execute() call and
    None on the second (direction-framework lookup); the endpoint falls
    back to an empty framework JSON in that case, which is fine for the
    smoke test because the Framework agent is patched anyway.
    """

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


def test_phase3_end_to_end_smoke(monkeypatch) -> None:
    """Upload → parse → session → WS init → 3 turns → report.

    Asserts the A4 invariants (pass_probability is a 0..100 int, reasons
    is populated with the verdict literal + turn index + quote,
    next_actions is populated) show up end-to-end in the polled report
    response.
    """
    from app.agents.compression.service import CompressionAgentService
    from app.agents.framework.service import FrameworkAgentService
    from app.agents.interviewer.service import InterviewerAgentService
    from app.agents.parse.service import ParseAgentService
    from app.agents.reference.service import ReferenceAgentService
    from app.agents.report.service import ReportAgentService
    from app.orchestrator import turn_graph as turn_graph_mod
    from app.ws import endpoint as ws_endpoint

    parse_out = _parse_payload()
    framework_out = _framework_payload()
    compression_out = _compression_payload()
    reference_out = _reference_payload()
    report_out = _report_payload()

    interviewer_calls = 0

    async def fake_parse_run(self, input, gateway):  # noqa: ANN001
        return parse_out

    async def fake_framework_run(self, input, gateway):  # noqa: ANN001
        return framework_out

    async def fake_interviewer_run(self, input, gateway):  # noqa: ANN001
        nonlocal interviewer_calls
        interviewer_calls += 1
        return _interviewer_payload(interviewer_calls)

    async def fake_compression_run(self, input, gateway):  # noqa: ANN001
        return compression_out

    async def fake_reference_run(self, input, gateway):  # noqa: ANN001
        return reference_out

    async def fake_report_run(self, input, gateway):  # noqa: ANN001
        return report_out

    async def fake_structured_completion(
        client, *, messages, response_model, max_retries=2
    ):  # noqa: ANN001
        # The inline turn_assessment node is the only Instructor call that
        # bypasses a dedicated agent service; intercept it here.
        if response_model is TurnAssessment:
            return TurnAssessment(
                summary="回答结构清晰但量化偏薄",
                strengths=["结构清楚"],
                weaknesses=["缺指标"],
            )
        raise AssertionError(f"unexpected response_model: {response_model}")

    monkeypatch.setattr(ParseAgentService, "run", fake_parse_run)
    monkeypatch.setattr(FrameworkAgentService, "run", fake_framework_run)
    monkeypatch.setattr(InterviewerAgentService, "run", fake_interviewer_run)
    monkeypatch.setattr(CompressionAgentService, "run", fake_compression_run)
    monkeypatch.setattr(ReferenceAgentService, "run", fake_reference_run)
    monkeypatch.setattr(ReportAgentService, "run", fake_report_run)
    monkeypatch.setattr(turn_graph_mod, "structured_completion", fake_structured_completion)

    headers = {"X-LLM-Config": _llm_config_header()}

    with TestClient(app) as client:
        # 1) Upload resume + JD.
        resume_response = client.post(
            "/api/v1/assets/resume",
            files={"file": ("resume.txt", b"candidate resume body", "text/plain")},
            headers=headers,
        )
        assert resume_response.status_code == 200, resume_response.text
        asset_id = resume_response.json()["asset_bundle_id"]

        jd_response = client.post(
            "/api/v1/assets/jd",
            files={"file": ("jd.txt", b"job description body", "text/plain")},
            data={"asset_bundle_id": asset_id},
            headers=headers,
        )
        assert jd_response.status_code == 200, jd_response.text

        # 2) Parse.
        parse_response = client.post(f"/api/v1/assets/{asset_id}/parse", headers=headers)
        assert parse_response.status_code == 200, parse_response.text
        assert parse_response.json()["payload"]["match_summary"] == parse_out.match_summary

        # 3) Create session.
        session_response = client.post(
            "/api/v1/sessions",
            json={
                "asset_bundle_id": asset_id,
                "config": {
                    "style": "standard_professional",
                    "direction": "project_deep_dive",
                    "duration_minutes": 20,
                },
            },
            headers=headers,
        )
        assert session_response.status_code == 200, session_response.text
        session_id = session_response.json()["session_id"]

        # 4) WS: patch the owner-check session factory to return a real
        # stub; the DB path is orthogonal to the orchestrator flow we
        # care about here.
        monkeypatch.setattr(
            ws_endpoint,
            "AsyncSessionFactory",
            lambda: _FakeDBSession(UUID(session_id)),
        )

        async def fake_get_ws_user(*_args: Any, **_kwargs: Any) -> AuthenticatedUser:
            return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)

        monkeypatch.setattr(ws_endpoint, "get_websocket_user", fake_get_ws_user)
        app.dependency_overrides[get_websocket_user] = fake_get_ws_user

        try:
            with client.websocket_connect(
                f"/ws/sessions/{session_id}?token=mock"
            ) as ws:
                ws.send_json(
                    {
                        "event": "client.session.init",
                        "config": {
                            "provider": "openai",
                            "api_key": "sk-e2e-test",
                            "model": "gpt-4o-mini",
                            "base_url": None,
                        },
                    }
                )

                # 5) Run three turns. Each turn emits assessed +
                # compressed + question events; the reference-answer task
                # is fire-and-forget and can interleave, so drain up to 5
                # events per turn and break once this turn's trio has
                # arrived. Track totals by type across the full session.
                counts = {
                    "server.turn.assessed": 0,
                    "server.turn.compressed": 0,
                    "server.question.generated": 0,
                }
                for turn_index in range(1, 4):
                    ws.send_json(
                        {
                            "event": "client.turn.end",
                            "turn_index": turn_index,
                            "question": f"Q{turn_index}",
                            "answer": f"A{turn_index} 是我们当时的决定",
                        }
                    )
                    got_trio = {k: False for k in counts}
                    for _ in range(5):
                        event = ws.receive_json()
                        name = event["event"]
                        if name in counts:
                            counts[name] += 1
                            got_trio[name] = True
                        if all(got_trio.values()):
                            break

                assert counts["server.turn.assessed"] == 3
                assert counts["server.turn.compressed"] == 3
                assert counts["server.question.generated"] == 3

                ws.send_json({"event": "client.session.end"})
        finally:
            app.dependency_overrides.pop(get_websocket_user, None)

        # 6) Trigger report + poll.
        trigger_response = client.post(
            f"/api/v1/sessions/{session_id}/report",
            json={},
            headers=headers,
        )
        assert trigger_response.status_code == 200, trigger_response.text
        assert trigger_response.json()["status"] == "generating"

        final_payload: dict[str, Any] | None = None
        deadline = time.time() + 5.0
        while time.time() < deadline:
            report_response = client.get(
                f"/api/v1/sessions/{session_id}/report", headers=headers
            )
            if report_response.status_code == 200:
                final_payload = report_response.json()
                break
            assert report_response.status_code == 409
            time.sleep(0.05)

    assert final_payload is not None, "report never transitioned to ready"
    payload = final_payload["payload"]

    # A4 invariants — pass_probability, reasons, next_actions.
    assert isinstance(payload["pass_probability"], int)
    assert 0 <= payload["pass_probability"] <= 100
    assert payload["pass_probability"] == 74

    assert len(payload["reasons"]) == 3
    for reason in payload["reasons"]:
        assert reason["verdict"] in {"strong", "solid", "mixed", "weak"}
        assert isinstance(reason["evidence_turn_index"], int)
        assert reason["evidence_turn_index"] >= 0
        assert isinstance(reason["quote"], str) and reason["quote"]
        assert isinstance(reason["aspect"], str) and reason["aspect"]

    assert len(payload["next_actions"]) == 3
    assert all(isinstance(n, str) and n for n in payload["next_actions"])

    assert payload["overall_summary"] == report_out.summary
