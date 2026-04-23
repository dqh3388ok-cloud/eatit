"""AzureASRBackend — streaming speech-to-text via azure-cognitiveservices-speech.

Architecture:
- We use `PushAudioInputStream` because the WebSocket hands us discrete chunks
  from `MediaRecorder`; we do not have a file or a classic audio device.
- `SpeechRecognizer` runs its own background thread; its `recognizing` and
  `recognized` events fire off-loop. We capture the current running loop in
  `start_stream` and call `loop.call_soon_threadsafe` to dispatch callbacks
  safely onto the event loop.
- `stop_stream` awaits `stop_continuous_recognition_async` via a Future so the
  final trailing event (Azure sometimes emits one after close) has a chance
  to land before we return.
- The Azure SDK is imported at function scope rather than module scope so tests
  that don't exercise AzureASRBackend directly don't pay the import cost and
  so missing SDK builds fail only when this backend is actually constructed.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable

from app.infra.asr.base import ASRBackend
from app.infra.asr.config import ASRConfig
from app.infra.asr.errors import ASRAuthError, ASRError, ASRNetworkError


class AzureASRBackend(ASRBackend):
    def __init__(self, config: ASRConfig) -> None:
        self._config = config
        self._partial_callbacks: list[Callable[[str], None]] = []
        self._final_callbacks: list[Callable[[str], None]] = []
        self._recognizer: Any | None = None
        self._push_stream: Any | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._started: bool = False
        self._stopped: bool = False

    def on_partial(self, callback: Callable[[str], None]) -> None:
        self._partial_callbacks.append(callback)

    def on_final(self, callback: Callable[[str], None]) -> None:
        self._final_callbacks.append(callback)

    async def start_stream(self) -> None:
        if self._started:
            raise ASRError("stream already started")
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError as exc:
            raise ASRError("azure-cognitiveservices-speech not installed") from exc

        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=self._config.subscription_key.get_secret_value(),
                region=self._config.region,
            )
            speech_config.speech_recognition_language = self._config.language

            audio_format = speechsdk.audio.AudioStreamFormat(
                compressed_stream_format=speechsdk.AudioStreamContainerFormat.ANY
            )
            push_stream = speechsdk.audio.PushAudioInputStream(audio_format)
            audio_config = speechsdk.audio.AudioConfig(stream=push_stream)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            if "auth" in message or "subscription" in message or "401" in message:
                raise ASRAuthError(str(exc)) from exc
            raise ASRError(str(exc)) from exc

        self._push_stream = push_stream
        self._recognizer = recognizer
        self._loop = asyncio.get_running_loop()

        recognizer.recognizing.connect(self._handle_recognizing)
        recognizer.recognized.connect(self._handle_recognized)
        recognizer.canceled.connect(self._handle_canceled)

        recognizer.start_continuous_recognition_async().get()
        self._started = True

    async def push_audio(self, chunk: bytes) -> None:
        if not self._started or self._stopped:
            raise ASRError("push_audio requires an active stream")
        assert self._push_stream is not None
        self._push_stream.write(chunk)

    async def stop_stream(self) -> None:
        if not self._started or self._stopped:
            return
        self._stopped = True
        assert self._recognizer is not None
        assert self._push_stream is not None
        self._push_stream.close()
        await asyncio.to_thread(self._recognizer.stop_continuous_recognition_async().get)

    def _dispatch(self, callbacks: list[Callable[[str], None]], text: str) -> None:
        if not text:
            return
        loop = self._loop
        if loop is None or loop.is_closed():
            return
        for cb in callbacks:
            loop.call_soon_threadsafe(cb, text)

    def _handle_recognizing(self, event: Any) -> None:
        self._dispatch(self._partial_callbacks, event.result.text or "")

    def _handle_recognized(self, event: Any) -> None:
        self._dispatch(self._final_callbacks, event.result.text or "")

    def _handle_canceled(self, event: Any) -> None:
        # Surface as a network-type error via the async side; we can't raise
        # from the SDK callback thread, so callers detect failure by timeout
        # on the final event. Log via stderr-safe print is out of scope here.
        reason = getattr(event, "error_details", "") or getattr(event, "reason", "")
        if not reason:
            return
        if any(tok in str(reason).lower() for tok in ("auth", "401", "subscription")):
            raise ASRAuthError(str(reason))
        raise ASRNetworkError(str(reason))
