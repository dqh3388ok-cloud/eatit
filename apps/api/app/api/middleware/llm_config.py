"""`X-LLM-Config` middleware.

Parses the header into `request.state.llm_config` as an LLMConfig. The raw header
and the parsed config MUST NOT be logged, breadcrumbed, or sent to Sentry. The
config lives only in request-scoped state and is discarded with the request.

On parse failure we return 400 with a generic message; the offending payload is
deliberately not echoed back.
"""

from __future__ import annotations

import base64
import binascii
import json

from pydantic import ValidationError
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from app.infra.llm import LLMConfig

HEADER_NAME = "X-LLM-Config"


class LLMConfigMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        raw_header = request.headers.get(HEADER_NAME)
        if raw_header:
            try:
                decoded_bytes = base64.b64decode(raw_header, validate=True)
                payload = json.loads(decoded_bytes.decode("utf-8"))
                request.state.llm_config = LLMConfig.model_validate(payload)
            except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValidationError):
                # Intentionally do NOT log the header or payload — leakage risk.
                return JSONResponse(
                    status_code=400,
                    content={"detail": f"Invalid {HEADER_NAME} header."},
                )
        return await call_next(request)
