"""ASR availability probe.

`GET /api/v1/asr/health` lets the desktop app learn whether the backend has
Azure Speech credentials configured, so the voice-mode UI can disable itself
and fall back to textarea input when the server cannot actually do ASR.

No secret material is exposed — only a boolean + provider name.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.infra.config import get_settings

router = APIRouter(prefix="/asr", tags=["asr"])


class ASRHealthResponse(BaseModel):
    available: bool
    provider: str


@router.get("/health", response_model=ASRHealthResponse)
async def asr_health() -> ASRHealthResponse:
    settings = get_settings()
    available = bool(settings.azure_speech_key) and bool(settings.azure_speech_region)
    return ASRHealthResponse(available=available, provider="azure")
