"""ASR infrastructure: pluggable speech-to-text backends.

Phase 4 introduced real-time voice interviews; the initial plan used Azure
Speech. The current backend is `faster-whisper` running on-device — zero
API key, zero network during transcription, ~142MB model downloaded to
`~/.cache/huggingface/` on first use.

Key invariants (carried forward from Phase 3/4 constraints):
- The backend interface is stable even though Whisper has no partial-
  transcript support; `on_partial` callbacks simply never fire. Future
  API-backed providers (with partials) plug in through the same contract.
- Sentry / log redaction rules still include `azure_speech` / `subscription`
  patterns so when we put an API provider back it's already covered.
"""

from app.infra.asr.base import ASRBackend
from app.infra.asr.config import ASRConfig
from app.infra.asr.errors import (
    ASRAuthError,
    ASRError,
    ASRNetworkError,
    ASRUnsupportedAudioError,
)
from app.infra.asr.factory import build_asr_backend
from app.infra.asr.mock_backend import MockASRBackend
from app.infra.asr.whisper_backend import WhisperASRBackend

__all__ = [
    "ASRBackend",
    "ASRConfig",
    "MockASRBackend",
    "WhisperASRBackend",
    "build_asr_backend",
    "ASRError",
    "ASRAuthError",
    "ASRNetworkError",
    "ASRUnsupportedAudioError",
]
