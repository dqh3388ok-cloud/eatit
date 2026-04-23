"""Regression: when ParseAgent raises an LLMError (e.g. context overflow,
auth), the HTTP layer must surface it as a 502 with a Chinese `detail`
message. Before this was fixed the exception bubbled as a raw 500, which
Starlette/CORSMiddleware could not decorate, and the desktop UI therefore
rendered a useless "Network Error".
"""

from __future__ import annotations

import base64
import json
from uuid import UUID

from httpx import ASGITransport, AsyncClient

from app.agents.parse.service import ParseAgentService
from app.api.dependencies.auth import (
    AuthenticatedUser,
    MOCK_USER_EMAIL,
    MOCK_USER_ID,
    get_current_user,
)
from app.infra.llm.errors import LLMError
from app.main import app


def _llm_config_header() -> str:
    return base64.b64encode(
        json.dumps(
            {
                "provider": "openai",
                "api_key": "sk-parse-error-test",
                "model": "gpt-4o-mini",
                "base_url": None,
            }
        ).encode("utf-8")
    ).decode("ascii")


async def _override_current_user() -> AuthenticatedUser:
    return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)


async def test_parse_llm_error_surfaces_as_502_with_detail(monkeypatch) -> None:
    from app.api.routes import assets as assets_routes

    asset_bundle_id = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f0e502")
    app.dependency_overrides[get_current_user] = _override_current_user

    # Short-circuit the asset / storage plumbing: the service lookup checks
    # that both files are uploaded; returning a minimal CandidateAsset is
    # enough to reach the ParseAgent call site.
    from app.models.asset import CandidateAsset

    class _StubStorage:
        async def download(self, _ref: str) -> bytes:
            return b"irrelevant"

    async def fake_get_owned(self, _session, _user, _asset_id):
        asset = CandidateAsset(
            id=str(asset_bundle_id),
            user_id=MOCK_USER_ID,
            resume_file_ref="mock/resume",
            jd_file_ref="mock/jd",
            status="ready_for_parse",
        )
        return asset

    async def exploding_run(self, _input, _gateway):
        raise LLMError(
            "litellm.BadRequestError: OpenAIException - This endpoint's "
            "maximum context length is 32768 tokens."
        )

    from app.domain.assets.service import AssetsService

    monkeypatch.setattr(AssetsService, "_get_owned_asset", fake_get_owned)
    monkeypatch.setattr(ParseAgentService, "run", exploding_run)
    monkeypatch.setattr(assets_routes, "get_storage", lambda: _StubStorage())

    async def fake_get_storage():
        return _StubStorage()

    from app.api.dependencies.storage import get_storage

    app.dependency_overrides[get_storage] = fake_get_storage

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                f"/api/v1/assets/{asset_bundle_id}/parse",
                headers={"X-LLM-Config": _llm_config_header()},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 502
    body = response.json()
    assert "LLM 调用失败" in body["detail"]
    assert "32768" in body["detail"]
