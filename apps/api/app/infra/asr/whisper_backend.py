"""WhisperASRBackend — on-device speech-to-text via faster-whisper.

Design notes:
- Whisper is not a streaming recognizer. We buffer every `push_audio` chunk
  in memory during the active stream and transcribe the full buffer when
  `stop_stream` is called. Partial (interim) transcripts are therefore NOT
  emitted; `on_partial` callbacks are registered but never fire. The
  UX in the desktop app is press-and-hold, so this matches user expectation
  (one final transcript per utterance).
- faster-whisper loads a ~142MB model from disk on first use
  (`~/.cache/huggingface/...`). We memoize the loaded model at class level
  so subsequent sessions reuse the same instance — first call in a process
  pays the load cost (or the network cost for the very first install), every
  call after is milliseconds to start.
- Incoming bytes come from MediaRecorder (WebM/Opus). We decode them to
  16 kHz mono float32 samples with PyAV (which ships bundled ffmpeg), then
  hand the numpy array to `model.transcribe(..., language=config.language)`.
- Callbacks fire from the asyncio-owned task that ran `stop_stream`; no
  cross-thread dispatch needed (unlike Azure). Still register callbacks
  defensively in lists so multiple observers work.
"""

from __future__ import annotations

import asyncio
import io
from typing import Any, Callable

from app.infra.asr.base import ASRBackend
from app.infra.asr.config import ASRConfig
from app.infra.asr.errors import ASRError, ASRUnsupportedAudioError


class WhisperASRBackend(ASRBackend):
    _model_cache: dict[tuple[str, str, str], Any] = {}

    def __init__(self, config: ASRConfig) -> None:
        self._config = config
        self._partial_callbacks: list[Callable[[str], None]] = []
        self._final_callbacks: list[Callable[[str], None]] = []
        self._buffer = bytearray()
        self._started: bool = False
        self._stopped: bool = False

    def on_partial(self, callback: Callable[[str], None]) -> None:
        # faster-whisper has no streaming partial, but we register for
        # interface parity — callback just never fires.
        self._partial_callbacks.append(callback)

    def on_final(self, callback: Callable[[str], None]) -> None:
        self._final_callbacks.append(callback)

    async def start_stream(self) -> None:
        if self._started:
            raise ASRError("stream already started")
        self._buffer = bytearray()
        self._started = True

    async def push_audio(self, chunk: bytes) -> None:
        if not self._started or self._stopped:
            raise ASRError("push_audio requires an active stream")
        self._buffer.extend(chunk)

    async def stop_stream(self) -> None:
        if not self._started or self._stopped:
            return
        self._stopped = True

        if len(self._buffer) == 0:
            return

        audio_bytes = bytes(self._buffer)
        self._buffer = bytearray()

        # Both decode and transcribe are CPU-heavy; offload so we don't
        # block the event loop. asyncio.to_thread returns the final text.
        try:
            text = await asyncio.to_thread(self._decode_and_transcribe, audio_bytes)
        except ASRError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ASRError(f"whisper transcription failed: {exc}") from exc

        if text:
            for cb in self._final_callbacks:
                cb(text)

    def _decode_and_transcribe(self, audio_bytes: bytes) -> str:
        samples = self._decode_to_mono16k(audio_bytes)
        if samples.size == 0:
            return ""
        model = self._load_model()
        segments, _info = model.transcribe(
            samples,
            language=self._config.language,
            beam_size=1,
            vad_filter=True,
        )
        # Materialize the generator; each segment is a namedtuple with .text
        return "".join(seg.text for seg in segments).strip()

    def _load_model(self) -> Any:
        key = (self._config.model_size, self._config.device, self._config.compute_type)
        cached = WhisperASRBackend._model_cache.get(key)
        if cached is not None:
            return cached
        try:
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ASRError("faster-whisper not installed") from exc

        model = WhisperModel(
            model_size_or_path=self._config.model_size,
            device=self._config.device,
            compute_type=self._config.compute_type,
        )
        WhisperASRBackend._model_cache[key] = model
        return model

    @staticmethod
    def _decode_to_mono16k(audio_bytes: bytes):
        """Decode a concatenation of MediaRecorder chunks (WebM/Opus or plain
        PCM) to a float32 mono numpy array at 16 kHz. Uses PyAV under the
        hood so we don't need a system ffmpeg install."""
        try:
            import av  # type: ignore
            import numpy as np
        except ImportError as exc:
            raise ASRError("PyAV / numpy not installed") from exc

        try:
            container = av.open(io.BytesIO(audio_bytes))
        except av.AVError as exc:
            raise ASRUnsupportedAudioError(f"could not open audio: {exc}") from exc

        stream = next((s for s in container.streams if s.type == "audio"), None)
        if stream is None:
            raise ASRUnsupportedAudioError("no audio stream in buffer")

        resampler = av.AudioResampler(format="flt", layout="mono", rate=16_000)
        chunks: list[Any] = []
        try:
            for frame in container.decode(stream):
                for resampled in resampler.resample(frame):
                    chunks.append(resampled.to_ndarray().reshape(-1))
            # flush the resampler
            for resampled in resampler.resample(None):
                chunks.append(resampled.to_ndarray().reshape(-1))
        finally:
            container.close()

        if not chunks:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(chunks).astype(np.float32)
