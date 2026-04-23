"""ASRBackend ABC — streaming speech-to-text contract.

Lifecycle:
    backend = build_asr_backend(config)
    backend.on_partial(lambda text: ...)
    backend.on_final(lambda text: ...)
    await backend.start_stream()
    await backend.push_audio(chunk_bytes)  # 0..N times
    await backend.stop_stream()

Callbacks fire from whatever thread / task the underlying SDK uses.
Implementations must marshal them back to the event loop before doing any
async work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Callable


class ASRBackend(ABC):
    @abstractmethod
    async def start_stream(self) -> None:
        """Open the streaming session. Must be called before `push_audio`."""

    @abstractmethod
    async def push_audio(self, chunk: bytes) -> None:
        """Push a raw audio chunk (opus/webm or pcm16, backend-specific)."""

    @abstractmethod
    async def stop_stream(self) -> None:
        """Close the stream. May trigger a trailing `on_final` emission."""

    @abstractmethod
    def on_partial(self, callback: Callable[[str], None]) -> None:
        """Register a callback for in-progress (interim) transcripts."""

    @abstractmethod
    def on_final(self, callback: Callable[[str], None]) -> None:
        """Register a callback for committed (endpointed) transcripts."""
