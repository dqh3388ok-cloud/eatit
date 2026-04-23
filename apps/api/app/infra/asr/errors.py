"""Typed ASR errors.

Business code should only catch these, never the raw Azure SDK exceptions.
The backend is the boundary that translates upstream exceptions into this
hierarchy.
"""

from __future__ import annotations


class ASRError(Exception):
    """Base for all ASR backend failures."""


class ASRAuthError(ASRError):
    """Upstream rejected the subscription key or region."""


class ASRNetworkError(ASRError):
    """Connection, timeout, or transient upstream failure."""


class ASRUnsupportedAudioError(ASRError):
    """Audio format / codec not supported by the backend."""
