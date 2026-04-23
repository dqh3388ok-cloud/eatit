"""MockASRBackend — deterministic stand-in for tests and for the dev mode
where Azure credentials are not configured.

Behavior:
- Records every pushed chunk in `self.pushed_chunks` so tests can assert
  they arrived.
- `emit_partial(text)` / `emit_final(text)` synchronously fan out to the
  registered callbacks; the orchestrator/ws tests use these to simulate
  Azure's recognizing / recognized events without timing flakiness.
- Lifecycle flags (`started`, `stopped`) mirror the ABC contract so tests
  can verify `stop_stream` was actually called during cleanup paths.
"""

from __future__ import annotations

from typing import Callable

from app.infra.asr.base import ASRBackend
from app.infra.asr.errors import ASRError


class MockASRBackend(ASRBackend):
    def __init__(self) -> None:
        self.pushed_chunks: list[bytes] = []
        self.started: bool = False
        self.stopped: bool = False
        self._partial_callbacks: list[Callable[[str], None]] = []
        self._final_callbacks: list[Callable[[str], None]] = []

    async def start_stream(self) -> None:
        if self.started:
            raise ASRError("stream already started")
        self.started = True

    async def push_audio(self, chunk: bytes) -> None:
        if not self.started or self.stopped:
            raise ASRError("push_audio requires an active stream")
        self.pushed_chunks.append(chunk)

    async def stop_stream(self) -> None:
        if not self.started:
            return
        self.stopped = True

    def on_partial(self, callback: Callable[[str], None]) -> None:
        self._partial_callbacks.append(callback)

    def on_final(self, callback: Callable[[str], None]) -> None:
        self._final_callbacks.append(callback)

    def emit_partial(self, text: str) -> None:
        for cb in self._partial_callbacks:
            cb(text)

    def emit_final(self, text: str) -> None:
        for cb in self._final_callbacks:
            cb(text)
