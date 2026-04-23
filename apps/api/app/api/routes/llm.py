"""LLM test endpoint.

`POST /api/v1/llm/test` — sends the spec prompt "Reply with OK only." through
the gateway and returns whether the round-trip succeeded plus tokens / latency.

On any LLM error we return 200 with `ok=False` + a typed `error_code` rather
than 5xx, so the frontend can render a friendly status without treating the
call as an infrastructure failure.
"""

from __future__ import annotations

import time
from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.dependencies.llm import get_llm_gateway
from app.infra.llm import LLMGateway
from app.infra.llm.errors import (
    LLMAuthError,
    LLMContentSafetyError,
    LLMError,
    LLMNetworkError,
    LLMRateLimitError,
)

router = APIRouter(prefix="/llm", tags=["llm"])

_TEST_PROMPT = "Reply with OK only."


class LLMUsage(BaseModel):
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int


class LLMTestResponse(BaseModel):
    ok: bool
    usage: LLMUsage | None = None
    error_code: str | None = None
    error_message: str | None = None


def _extract_usage(response: Any, latency_ms: int) -> LLMUsage:
    usage = getattr(response, "usage", None) or (
        response.get("usage") if isinstance(response, dict) else None
    )
    prompt_tokens = 0
    completion_tokens = 0
    if usage is not None:
        prompt_tokens = int(
            getattr(usage, "prompt_tokens", None)
            or (usage.get("prompt_tokens") if isinstance(usage, dict) else 0)
            or 0
        )
        completion_tokens = int(
            getattr(usage, "completion_tokens", None)
            or (usage.get("completion_tokens") if isinstance(usage, dict) else 0)
            or 0
        )
    return LLMUsage(
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        latency_ms=latency_ms,
    )


@router.post("/test", response_model=LLMTestResponse)
async def test_llm_connection(
    gateway: LLMGateway = Depends(get_llm_gateway),
) -> LLMTestResponse:
    started = time.perf_counter()
    try:
        response = await gateway.complete(
            messages=[{"role": "user", "content": _TEST_PROMPT}],
            max_tokens=16,
        )
    except LLMAuthError as exc:
        return LLMTestResponse(ok=False, error_code="auth", error_message=str(exc))
    except LLMRateLimitError as exc:
        return LLMTestResponse(ok=False, error_code="rate_limit", error_message=str(exc))
    except LLMNetworkError as exc:
        return LLMTestResponse(ok=False, error_code="network", error_message=str(exc))
    except LLMContentSafetyError as exc:
        return LLMTestResponse(ok=False, error_code="content_safety", error_message=str(exc))
    except LLMError as exc:
        return LLMTestResponse(ok=False, error_code="unknown", error_message=str(exc))

    latency_ms = int((time.perf_counter() - started) * 1000)
    return LLMTestResponse(ok=True, usage=_extract_usage(response, latency_ms))
