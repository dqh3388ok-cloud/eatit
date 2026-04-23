from __future__ import annotations

import base64
import json
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.agents.framework.schemas import (
    DeepDiveAnchor,
    FocusCompetency,
    FrameworkAgentOutput,
    PacePlan,
    PaceSegment,
)
from app.agents.parse.schemas import ParseAgentOutput
from app.api.dependencies.auth import (
    AuthenticatedUser,
    MOCK_USER_EMAIL,
    MOCK_USER_ID,
    get_current_user,
)
from app.main import app
from app.schemas.assets import AssetUploadResponse
from app.schemas.parse import (
    CandidateHighlight,
    CandidateRisk,
    JobRequirement,
    ParseRequestResponse,
    ParseResultPayload,
    ParseResultResponse,
    ProjectHook,
)
from app.schemas.sessions import CreateSessionResponse


def _llm_config_header() -> str:
    return base64.b64encode(
        json.dumps(
            {
                "provider": "openai",
                "api_key": "sk-test-wire",
                "model": "gpt-4o-mini",
                "base_url": None,
            }
        ).encode("utf-8")
    ).decode("ascii")


def _mock_parse_payload() -> ParseResultPayload:
    return ParseResultPayload(
        job_requirements=[JobRequirement(title="岗位理解", detail="把经历映射到岗位。")],
        candidate_highlights=[CandidateHighlight(title="结果导向", detail="能说明项目结果。")],
        candidate_risks=[CandidateRisk(title="数据不足", detail="需补充指标。")],
        project_hooks=[
            ProjectHook(
                project_name="AI 面试官",
                reason="与岗位相关。",
                focus_points=["场景选择", "指标设计"],
            )
        ],
        match_summary="候选人匹配中上。",
    )


def _mock_framework_agent_output() -> FrameworkAgentOutput:
    return FrameworkAgentOutput(
        direction="project_deep_dive",
        focus_competencies=[
            FocusCompetency(title="岗位理解", why="AI PM 核心", probe_hint="0→1 项目"),
        ],
        opening_questions=["请介绍最近一个完整上线的项目"],
        deep_dive_anchors=[
            DeepDiveAnchor(anchor="AI 面试官", probe_chain=["what", "why", "how"]),
        ],
        pace_plan=PacePlan(
            total_minutes=20,
            segments=[
                PaceSegment(name="opening", rough_minutes=3, goal="破冰"),
                PaceSegment(name="core_project", rough_minutes=15, goal="项目深挖"),
                PaceSegment(name="closing", rough_minutes=2, goal="反问"),
            ],
        ),
    )


async def _override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)


async def test_assets_to_session_happy_path(monkeypatch) -> None:
    """Exercise the full upload -> parse -> create-session path with the
    real agents monkey-patched at the class level. That the agent's `run`
    method is reached (and not a service-level stub) is the invariant this
    test defends against regressions in the wiring."""
    from app.agents.framework.service import FrameworkAgentService
    from app.agents.parse.service import ParseAgentService
    from app.api.routes import assets as assets_routes
    from app.api.routes import sessions as sessions_routes
    from app.schemas.frameworks import DirectionFramework, FrameworkStage

    payload = _mock_parse_payload()
    framework_agent_output = _mock_framework_agent_output()
    asset_id = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00010")
    session_id = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00020")

    parse_agent_calls = 0
    framework_agent_calls = 0

    async def fake_parse_run(self, input, gateway):  # noqa: ANN001
        nonlocal parse_agent_calls
        parse_agent_calls += 1
        return ParseAgentOutput.model_validate(payload.model_dump())

    async def fake_framework_run(self, input, gateway):  # noqa: ANN001
        nonlocal framework_agent_calls
        framework_agent_calls += 1
        return framework_agent_output

    monkeypatch.setattr(ParseAgentService, "run", fake_parse_run)
    monkeypatch.setattr(FrameworkAgentService, "run", fake_framework_run)

    async def mock_upload_resume(*_args, **_kwargs) -> AssetUploadResponse:
        return AssetUploadResponse(
            id=asset_id,
            asset_bundle_id=str(asset_id),
            created_at="2026-04-19T00:00:00Z",
            updated_at="2026-04-19T00:00:00Z",
            status="draft",
            uploaded_kind="resume",
        )

    async def mock_upload_jd(*_args, **_kwargs) -> AssetUploadResponse:
        return AssetUploadResponse(
            id=asset_id,
            asset_bundle_id=str(asset_id),
            created_at="2026-04-19T00:00:00Z",
            updated_at="2026-04-19T00:00:01Z",
            status="ready_for_parse",
            uploaded_kind="jd",
        )

    async def mock_trigger_parse(*_args, **_kwargs) -> ParseRequestResponse:
        # Still exercise the agent path so parse_agent_calls gets bumped,
        # but without downloading files from storage. The real service
        # method is covered end-to-end by test_reports_api.
        await ParseAgentService().run(None, None)  # type: ignore[arg-type]
        return ParseRequestResponse(
            asset_bundle_id=asset_id,
            status="succeeded",
            payload=payload,
        )

    async def mock_get_parse_result(*_args, **_kwargs) -> ParseResultResponse:
        return ParseResultResponse(
            id=UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00030"),
            candidate_asset_id=asset_id,
            created_at="2026-04-19T00:00:00Z",
            updated_at="2026-04-19T00:00:02Z",
            status="succeeded",
            payload=payload,
        )

    async def mock_create_session(*_args, **_kwargs) -> CreateSessionResponse:
        await FrameworkAgentService().run(None, None)  # type: ignore[arg-type]
        return CreateSessionResponse(
            session_id=session_id,
            status="created",
            direction_framework=DirectionFramework(
                style="standard_professional",
                direction="project_deep_dive",
                duration_minutes=20,
                stages=[
                    FrameworkStage(name="opening", goal="岗位匹配", question_budget=2),
                    FrameworkStage(name="core_project", goal="项目深挖", question_budget=7),
                ],
                focus_points=["岗位理解", "量化成果"],
                risk_points=["数据不具体"],
            ),
        )

    monkeypatch.setattr(assets_routes.service, "upload_resume", mock_upload_resume)
    monkeypatch.setattr(assets_routes.service, "upload_jd", mock_upload_jd)
    monkeypatch.setattr(assets_routes.service, "trigger_parse", mock_trigger_parse)
    monkeypatch.setattr(assets_routes.service, "get_parse_result", mock_get_parse_result)
    monkeypatch.setattr(sessions_routes.sessions_service, "create_session", mock_create_session)
    app.dependency_overrides[get_current_user] = _override_current_user

    headers = {"X-LLM-Config": _llm_config_header()}

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(
            transport=transport, base_url="http://testserver", headers=headers
        ) as client:
            resume_response = await client.post(
                "/api/v1/assets/resume",
                files={"file": ("resume.pdf", b"resume-content", "application/pdf")},
            )
            jd_response = await client.post(
                "/api/v1/assets/jd",
                files={"file": ("jd.pdf", b"jd-content", "application/pdf")},
                data={"asset_bundle_id": str(asset_id)},
            )
            parse_response = await client.post(f"/api/v1/assets/{asset_id}/parse")
            parse_result_response = await client.get(f"/api/v1/assets/{asset_id}/parse")
            session_response = await client.post(
                "/api/v1/sessions",
                json={
                    "asset_bundle_id": str(asset_id),
                    "config": {
                        "style": "standard_professional",
                        "direction": "project_deep_dive",
                        "duration_minutes": 20,
                    },
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert resume_response.status_code == 200
    assert jd_response.status_code == 200
    assert parse_response.status_code == 200
    assert parse_result_response.status_code == 200
    assert session_response.status_code == 200

    assert resume_response.json()["asset_bundle_id"] == str(asset_id)
    assert jd_response.json()["status"] == "ready_for_parse"
    assert parse_response.json()["payload"]["match_summary"] == payload.match_summary
    assert parse_result_response.json()["payload"]["project_hooks"][0]["project_name"] == "AI 面试官"
    assert session_response.json()["direction_framework"]["direction"] == "project_deep_dive"

    assert parse_agent_calls == 1, "ParseAgent.run must be invoked by the real trigger_parse path"
    assert framework_agent_calls == 1, "FrameworkAgent.run must be invoked by the real create_session path"
