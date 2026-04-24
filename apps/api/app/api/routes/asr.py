"""ASR availability probe.

`GET /api/v1/asr/health` lets the desktop app learn whether the backend
can do speech-to-text, so the voice-mode UI can disable itself and fall
back to textarea input when the runtime isn't usable.

For the current on-device backend (faster-whisper) the probe is satisfied
as long as the library is importable — no API keys, no network, no region
selection involved. The response shape is preserved from the previous
Azure-backed version so the desktop app doesn't need to fork on providers.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/asr", tags=["asr"])


class ASRHealthResponse(BaseModel):
    available: bool
    provider: str


@router.get("/health", response_model=ASRHealthResponse)
async def asr_health() -> ASRHealthResponse:
    try:
        import faster_whisper  # noqa: F401
        import av  # noqa: F401
    except ImportError:
        return ASRHealthResponse(available=False, provider="whisper")
    return ASRHealthResponse(available=True, provider="whisper")
