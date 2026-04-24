"""ASR backend factory.

Current provider: `faster-whisper` (on-device, MIT-licensed, no API key).
When we later add an API provider back (e.g. Azure Speech, Deepgram), add
its backend module and dispatch on `config.provider`.
"""

from __future__ import annotations

from app.infra.asr.base import ASRBackend
from app.infra.asr.config import ASRConfig
from app.infra.asr.errors import ASRError
from app.infra.config import get_settings


def build_asr_backend(config: ASRConfig | None = None) -> ASRBackend:
    from app.infra.asr.whisper_backend import WhisperASRBackend

    if config is None:
        settings = get_settings()
        config = ASRConfig(model_size=settings.asr_model_size)

    if config.provider == "whisper":
        return WhisperASRBackend(config)
    raise ASRError(f"unsupported ASR provider: {config.provider}")
