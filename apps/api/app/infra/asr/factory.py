"""ASR backend factory.

Reads the server-side env (AZURE_SPEECH_KEY + AZURE_SPEECH_REGION) via
`get_settings()` when no explicit config is passed. Tests build configs
directly or instantiate `MockASRBackend` without going through this factory.
"""

from __future__ import annotations

from pydantic import SecretStr

from app.infra.asr.base import ASRBackend
from app.infra.asr.config import ASRConfig
from app.infra.asr.errors import ASRError
from app.infra.config import get_settings


def build_asr_backend(config: ASRConfig | None = None) -> ASRBackend:
    from app.infra.asr.azure_backend import AzureASRBackend

    if config is None:
        settings = get_settings()
        if not settings.azure_speech_key or not settings.azure_speech_region:
            raise ASRError(
                "azure speech credentials not configured; set AZURE_SPEECH_KEY + "
                "AZURE_SPEECH_REGION in .env"
            )
        config = ASRConfig(
            subscription_key=SecretStr(settings.azure_speech_key),
            region=settings.azure_speech_region,
        )

    if config.provider == "azure":
        return AzureASRBackend(config)
    raise ASRError(f"unsupported ASR provider: {config.provider}")
