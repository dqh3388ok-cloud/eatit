from __future__ import annotations

import base64
import io
import json
import logging
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import AsyncMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


SECRET = "sk-middleware-test-7bc2a"


def _encode_config(payload: dict) -> str:
    return base64.b64encode(json.dumps(payload).encode("utf-8")).decode("ascii")


@pytest.fixture
def config_header() -> str:
    return _encode_config(
        {
            "provider": "openai",
            "api_key": SECRET,
            "model": "gpt-4o-mini",
            "base_url": None,
        }
    )


async def test_llm_test_without_header_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/llm/test")

    assert response.status_code == 400
    assert "X-LLM-Config" in response.json()["detail"]


async def test_llm_test_with_invalid_base64_returns_400() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post(
            "/api/v1/llm/test",
            headers={"X-LLM-Config": "this is !! not base64"},
        )

    assert response.status_code == 400


async def test_llm_test_with_non_json_body_returns_400() -> None:
    payload = base64.b64encode(b"not-json-not-even-close").decode("ascii")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/llm/test", headers={"X-LLM-Config": payload})

    assert response.status_code == 400


async def test_llm_test_with_missing_required_field_returns_400() -> None:
    payload = _encode_config({"provider": "openai"})  # no api_key, no model
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.post("/api/v1/llm/test", headers={"X-LLM-Config": payload})

    assert response.status_code == 400


async def test_llm_test_happy_path(config_header: str) -> None:
    async def fake_completion(*_args, **_kwargs):
        return {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"prompt_tokens": 7, "completion_tokens": 1},
        }

    transport = ASGITransport(app=app)
    with patch("app.infra.llm.gateway.litellm.acompletion", new=fake_completion):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/llm/test", headers={"X-LLM-Config": config_header}
            )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is True
    assert body["usage"]["prompt_tokens"] == 7
    assert body["usage"]["completion_tokens"] == 1
    assert body["usage"]["latency_ms"] >= 0


async def test_llm_test_auth_error_returns_ok_false(config_header: str) -> None:
    from litellm.exceptions import AuthenticationError

    transport = ASGITransport(app=app)
    err = AuthenticationError(message="bad", llm_provider="openai", model="gpt-4o-mini")
    with patch(
        "app.infra.llm.gateway.litellm.acompletion",
        new=AsyncMock(side_effect=err),
    ):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            response = await client.post(
                "/api/v1/llm/test", headers={"X-LLM-Config": config_header}
            )

    assert response.status_code == 200
    body = response.json()
    assert body["ok"] is False
    assert body["error_code"] == "auth"


async def test_llm_test_does_not_leak_key_into_logs(config_header: str, caplog) -> None:
    async def fake_completion(*_args, **_kwargs):
        return {
            "choices": [{"message": {"content": "OK"}}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 1},
        }

    # Capture logs from every logger at the root
    caplog.set_level(logging.DEBUG)

    # Also capture stdout/stderr because structlog renders to stdout, not stdlib logging
    stdout_buf = io.StringIO()
    stderr_buf = io.StringIO()

    transport = ASGITransport(app=app)
    with patch("app.infra.llm.gateway.litellm.acompletion", new=fake_completion):
        with redirect_stdout(stdout_buf), redirect_stderr(stderr_buf):
            async with AsyncClient(transport=transport, base_url="http://testserver") as client:
                response = await client.post(
                    "/api/v1/llm/test", headers={"X-LLM-Config": config_header}
                )

    assert response.status_code == 200

    combined = " ".join(
        [
            stdout_buf.getvalue(),
            stderr_buf.getvalue(),
            *[record.getMessage() for record in caplog.records],
        ]
    )

    assert SECRET not in combined, "api_key leaked into logs/stdout/stderr"
    # Also guard against the raw b64-encoded header making it into logs
    assert config_header not in combined
