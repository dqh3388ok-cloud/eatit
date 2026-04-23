from __future__ import annotations

import base64
import json

import anyio
from httpx import ASGITransport, AsyncClient

from app.agents.framework.schemas import (
    DeepDiveAnchor,
    FocusCompetency,
    FrameworkAgentOutput,
    PacePlan,
    PaceSegment,
)
from app.agents.parse.schemas import ParseAgentOutput
from app.agents.report.schemas import Reason, ReportAgentOutput
from app.main import app


def _llm_config_header() -> str:
    return base64.b64encode(
        json.dumps(
            {
                "provider": "openai",
                "api_key": "sk-report-wire",
                "model": "gpt-4o-mini",
                "base_url": None,
            }
        ).encode("utf-8")
    ).decode("ascii")


def _fake_parse_output() -> ParseAgentOutput:
    return ParseAgentOutput.model_validate(
        {
            "job_requirements": [{"title": "岗位理解", "detail": "把经历映射到岗位。"}],
            "candidate_highlights": [{"title": "结果导向", "detail": "能说明项目结果。"}],
            "candidate_risks": [{"title": "数据不足", "detail": "需要补充指标。"}],
            "project_hooks": [
                {
                    "project_name": "AI 面试官",
                    "reason": "与岗位相关。",
                    "focus_points": ["场景选择", "指标设计"],
                }
            ],
            "match_summary": "候选人匹配中上。",
        }
    )


def _fake_framework_output() -> FrameworkAgentOutput:
    return FrameworkAgentOutput(
        direction="project_deep_dive",
        focus_competencies=[FocusCompetency(title="岗位理解", why="AI PM 核心", probe_hint="0→1 项目")],
        opening_questions=["请介绍最近一个完整上线的项目"],
        deep_dive_anchors=[DeepDiveAnchor(anchor="AI 面试官", probe_chain=["what", "why", "how"])],
        pace_plan=PacePlan(
            total_minutes=20,
            segments=[
                PaceSegment(name="opening", rough_minutes=3, goal="破冰"),
                PaceSegment(name="core_project", rough_minutes=15, goal="项目深挖"),
                PaceSegment(name="closing", rough_minutes=2, goal="反问"),
            ],
        ),
    )


def _fake_report_output() -> ReportAgentOutput:
    return ReportAgentOutput(
        pass_probability=72,
        summary="候选人整体胜任,但若干维度需要复盘。",
        reasons=[
            Reason(
                aspect="指标设计",
                verdict="solid",
                evidence_turn_index=0,
                quote="完成率作为北极星指标",
            ),
            Reason(
                aspect="失败复盘",
                verdict="weak",
                evidence_turn_index=1,
                quote="主要是配合执行",
            ),
        ],
        next_actions=["整理上线指标表", "复盘失败项目"],
    )


async def test_trigger_report_completes_via_asyncio_task_queue(monkeypatch) -> None:
    """End-to-end: upload -> parse -> create session -> trigger report -> poll.
    All three agents are monkey-patched at the class level so the real service
    bodies run (real DB + real task queue) while the LLM calls are stubbed."""
    from app.agents.framework.service import FrameworkAgentService
    from app.agents.parse.service import ParseAgentService
    from app.agents.report.service import ReportAgentService

    parse_out = _fake_parse_output()
    framework_out = _fake_framework_output()
    report_out = _fake_report_output()

    async def fake_parse_run(self, input, gateway):  # noqa: ANN001
        return parse_out

    async def fake_framework_run(self, input, gateway):  # noqa: ANN001
        return framework_out

    async def fake_report_run(self, input, gateway):  # noqa: ANN001
        return report_out

    monkeypatch.setattr(ParseAgentService, "run", fake_parse_run)
    monkeypatch.setattr(FrameworkAgentService, "run", fake_framework_run)
    monkeypatch.setattr(ReportAgentService, "run", fake_report_run)

    headers = {"X-LLM-Config": _llm_config_header()}
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://testserver", headers=headers
    ) as client:
        resume_response = await client.post(
            "/api/v1/assets/resume",
            files={"file": ("resume.txt", b"resume-content", "text/plain")},
        )
        asset_id = resume_response.json()["asset_bundle_id"]

        await client.post(
            "/api/v1/assets/jd",
            files={"file": ("jd.txt", b"jd-content", "text/plain")},
            data={"asset_bundle_id": asset_id},
        )
        await client.post(f"/api/v1/assets/{asset_id}/parse")
        session_response = await client.post(
            "/api/v1/sessions",
            json={
                "asset_bundle_id": asset_id,
                "config": {
                    "style": "standard_professional",
                    "direction": "project_deep_dive",
                    "duration_minutes": 20,
                },
            },
        )
        session_id = session_response.json()["session_id"]

        trigger_response = await client.post(f"/api/v1/sessions/{session_id}/report", json={})

        assert trigger_response.status_code == 200
        assert trigger_response.json()["status"] == "generating"

        final_status_code = 0
        final_payload: dict[str, object] | None = None
        for _ in range(20):
            report_response = await client.get(f"/api/v1/sessions/{session_id}/report")
            final_status_code = report_response.status_code
            if report_response.status_code == 200:
                final_payload = report_response.json()
                break
            assert report_response.status_code == 409
            await anyio.sleep(0.05)

    assert final_status_code == 200
    assert final_payload is not None
    assert final_payload["status"] == "ready"
    assert final_payload["payload"]["pass_probability"] == 72
    assert len(final_payload["payload"]["reasons"]) == 2
    assert "整理" in final_payload["payload"]["next_actions"][0]
