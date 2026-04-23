"""Unified exception handlers (Phase 5 §P5.6a).

Every error path should come back to the desktop as a purposeful JSON
body with `{detail, request_id, code}`. Subclasses of LLMError and
ASRError get friendly Chinese detail strings; SQLAlchemy constraint
violations surface as 409; everything else becomes a 500.

The `request_id` is attached both to the response body and the response
header so the desktop client can surface it in a toast / bug report
without reading headers (which some transports strip).
"""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.infra.asr.errors import (
    ASRAuthError,
    ASRError,
    ASRNetworkError,
    ASRUnsupportedAudioError,
)
from app.infra.llm.errors import (
    LLMAuthError,
    LLMContentSafetyError,
    LLMError,
    LLMNetworkError,
    LLMRateLimitError,
)
from app.infra.logging import get_logger


_logger = get_logger(__name__)


def _request_id() -> str:
    return uuid.uuid4().hex[:12]


def _json_error(
    *,
    status_code: int,
    code: str,
    detail: str,
    request_id: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail, "request_id": request_id, "code": code},
        headers={"X-Request-Id": request_id},
    )


async def _handle_llm_error(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id()
    if isinstance(exc, LLMAuthError):
        detail = "LLM 鉴权失败,请在「设置」里检查 API Key。"
        code = "llm_auth"
    elif isinstance(exc, LLMRateLimitError):
        detail = "LLM 达到调用限频,请稍后重试或更换 Provider。"
        code = "llm_rate_limit"
    elif isinstance(exc, LLMNetworkError):
        detail = "与 LLM 供应商通讯异常,请检查网络后重试。"
        code = "llm_network"
    elif isinstance(exc, LLMContentSafetyError):
        detail = "请求被 LLM 内容安全策略拦截,请调整输入。"
        code = "llm_content_safety"
    else:
        detail = "LLM 调用失败,请稍后重试。"
        code = "llm_error"
    _logger.error(
        "llm.error",
        request_id=rid,
        method=request.method,
        path=request.url.path,
        exc_type=type(exc).__name__,
    )
    return _json_error(status_code=502, code=code, detail=detail, request_id=rid)


async def _handle_asr_error(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id()
    if isinstance(exc, ASRAuthError):
        detail = "Azure Speech 鉴权失败,请检查服务端 .env 中的密钥。"
        code = "asr_auth"
    elif isinstance(exc, ASRNetworkError):
        detail = "与 Azure Speech 通讯异常,请检查网络后重试。"
        code = "asr_network"
    elif isinstance(exc, ASRUnsupportedAudioError):
        detail = "当前浏览器/麦克风采集到的音频格式 Azure 不支持。"
        code = "asr_unsupported_audio"
    else:
        detail = "语音识别服务暂不可用,请检查服务端配置后重试。"
        code = "asr_error"
    _logger.error(
        "asr.error",
        request_id=rid,
        method=request.method,
        path=request.url.path,
        exc_type=type(exc).__name__,
    )
    return _json_error(status_code=503, code=code, detail=detail, request_id=rid)


async def _handle_integrity_error(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id()
    _logger.error(
        "db.integrity_error",
        request_id=rid,
        method=request.method,
        path=request.url.path,
        exc_type=type(exc).__name__,
    )
    return _json_error(
        status_code=409,
        code="db_integrity",
        detail="数据冲突,请刷新页面后重试。",
        request_id=rid,
    )


async def _handle_sqlalchemy_error(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id()
    _logger.error(
        "db.error",
        request_id=rid,
        method=request.method,
        path=request.url.path,
        exc_type=type(exc).__name__,
    )
    return _json_error(
        status_code=500,
        code="db_error",
        detail="数据库异常,请稍后重试。",
        request_id=rid,
    )


async def _handle_uncaught(request: Request, exc: Exception) -> JSONResponse:
    rid = _request_id()
    _logger.error(
        "unhandled.exception",
        request_id=rid,
        method=request.method,
        path=request.url.path,
        exc_type=type(exc).__name__,
        exc_message=str(exc),
    )
    return _json_error(
        status_code=500,
        code="internal_error",
        detail="内部错误,请稍后重试。",
        request_id=rid,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app.

    Order matters: more specific subclasses before broader ones. FastAPI
    dispatches by the registered class, preferring the most specific
    match, so registering `IntegrityError` alongside `SQLAlchemyError`
    + `Exception` is safe.
    """
    app.add_exception_handler(LLMError, _handle_llm_error)
    app.add_exception_handler(ASRError, _handle_asr_error)
    app.add_exception_handler(IntegrityError, _handle_integrity_error)
    app.add_exception_handler(SQLAlchemyError, _handle_sqlalchemy_error)
    app.add_exception_handler(Exception, _handle_uncaught)


# Re-exported so tests can inspect mappings without relying on FastAPI's
# handler registry.
__all__: list[str] = ["register_exception_handlers"]
_ = (
    Any,  # for future-proofing if handler signatures widen
)
