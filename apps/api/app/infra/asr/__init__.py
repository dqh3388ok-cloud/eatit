"""ASR infrastructure: pluggable speech-to-text backends.

Phase 4 introduces real-time voice interviews. ASR (Automatic Speech Recognition)
lives behind an abstraction so business code never touches vendor SDKs directly
and so tests can swap in a mock backend without pulling vendor credentials.

Key invariants (per Phase 3/4 constraints):
- The secret is a `SecretStr`; retrieve only via `.get_secret_value()` at the
  exact call site that hands it to the SDK.
- Unlike `LLMConfig`, the ASR key is server-side `.env`, not BYOK-per-request —
  the Azure SDK requires it at construction time and this is a single-machine
  single-user desktop app.
- Secret tokens are referenced only in this package's config / factory /
  azure_backend modules; a meta-test enforces no leakage elsewhere.
"""

from app.infra.asr.azure_backend import AzureASRBackend
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

__all__ = [
    "ASRBackend",
    "ASRConfig",
    "AzureASRBackend",
    "MockASRBackend",
    "build_asr_backend",
    "ASRError",
    "ASRAuthError",
    "ASRNetworkError",
    "ASRUnsupportedAudioError",
]
