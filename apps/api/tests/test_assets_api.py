from __future__ import annotations

from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.api.dependencies.auth import AuthenticatedUser, MOCK_USER_EMAIL, MOCK_USER_ID, get_current_user
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


def _mock_parse_payload() -> ParseResultPayload:
    return ParseResultPayload(
        job_requirements=[
            JobRequirement(title="岗位理解", detail="需要把项目经历映射到目标岗位。"),
        ],
        candidate_highlights=[
            CandidateHighlight(title="结果导向", detail="能够说明项目结果。"),
        ],
        candidate_risks=[
            CandidateRisk(title="数据不足", detail="需要补充更具体的业务指标。"),
        ],
        project_hooks=[
            ProjectHook(
                project_name="AI 面试官",
                reason="与目标岗位相关性高。",
                focus_points=["场景选择", "指标设计"],
            )
        ],
        match_summary="候选人与岗位总体匹配，但还需要补充量化结果。",
    )


async def _override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)


async def test_assets_to_session_happy_path(monkeypatch) -> None:
    from app.api.routes import assets as assets_routes
    from app.api.routes import sessions as sessions_routes
    from app.schemas.frameworks import DirectionFramework, FrameworkStage

    payload = _mock_parse_payload()
    asset_id = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00010")
    session_id = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00020")

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

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
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
