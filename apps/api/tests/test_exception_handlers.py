"""Tests for Phase 5 P5.6a unified exception handlers.

Rather than reach into the running app, we spin up a minimal FastAPI
instance that calls `register_exception_handlers(app)` and then attach
routes that deliberately raise the different error types. That exercises
the actual handler mappings without mutating the production routes."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError

from app.api.exception_handlers import register_exception_handlers
from app.infra.llm.errors import LLMAuthError


def _build_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/boom/unknown")
    async def boom_unknown() -> None:
        raise RuntimeError("surprise: nothing mapped this")

    @app.get("/boom/llm-auth")
    async def boom_llm_auth() -> None:
        raise LLMAuthError("bad api key")

    @app.get("/boom/integrity")
    async def boom_integrity() -> None:
        raise IntegrityError("INSERT ...", params={}, orig=Exception("UNIQUE failed"))

    return app


def test_uncaught_exception_returns_friendly_500() -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom/unknown")

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "内部错误,请稍后重试。"
    assert body["code"] == "internal_error"
    assert isinstance(body["request_id"], str) and body["request_id"]
    # Request ID is mirrored in the response header so transports that
    # can't read the JSON body still have a handle.
    assert response.headers.get("X-Request-Id") == body["request_id"]


def test_llm_auth_error_maps_to_502_with_friendly_copy() -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom/llm-auth")

    assert response.status_code == 502
    body = response.json()
    assert body["code"] == "llm_auth"
    assert "API Key" in body["detail"]
    assert isinstance(body["request_id"], str) and body["request_id"]


def test_integrity_error_maps_to_409_with_friendly_copy() -> None:
    client = TestClient(_build_app(), raise_server_exceptions=False)

    response = client.get("/boom/integrity")

    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "db_integrity"
    assert "数据冲突" in body["detail"]
    assert isinstance(body["request_id"], str) and body["request_id"]
