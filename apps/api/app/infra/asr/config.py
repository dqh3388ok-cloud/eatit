"""ASRConfig — local Whisper runtime configuration.

No secrets: the current backend (faster-whisper) runs fully on-device, so
there's nothing to mask. The SecretStr scaffold from the Azure version is
gone; when we later add an API-backed alternative we'll restore it via a
dedicated subclass rather than bloating the shared config.

`frozen=True` prevents post-construction mutation so the factory can
memoize built backends without worrying about identity drift.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ASRConfig(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    provider: str = "whisper"
    # faster-whisper model size. "base" = 142MB, good zh baseline on M1 ~2s/30s audio.
    # Heavier options: "small" (466MB), "medium" (1.5GB), "large-v3" (3GB).
    model_size: str = "base"
    language: str = "zh"
    # CTranslate2 compute type. "int8" is the best speed/quality trade-off on
    # CPU (Apple Silicon included). Users who want more accuracy can bump to
    # "float16" on GPU-equipped boxes.
    compute_type: str = "int8"
    device: str = "cpu"
