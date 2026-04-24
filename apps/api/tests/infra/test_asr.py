from __future__ import annotations

import pathlib

import pytest

from app.infra.asr import (
    ASRConfig,
    ASRError,
    ASRUnsupportedAudioError,
    MockASRBackend,
    WhisperASRBackend,
    build_asr_backend,
)


def _whisper_config(**overrides) -> ASRConfig:
    data = {"model_size": "base", "language": "zh"}
    data.update(overrides)
    return ASRConfig(**data)


def test_asr_config_defaults_to_whisper_provider() -> None:
    config = _whisper_config()

    assert config.provider == "whisper"
    assert config.model_size == "base"
    assert config.language == "zh"
    assert config.compute_type == "int8"
    assert config.device == "cpu"


def test_build_asr_backend_returns_whisper_backend() -> None:
    backend = build_asr_backend(_whisper_config())

    assert isinstance(backend, WhisperASRBackend)


def test_build_asr_backend_rejects_unknown_provider() -> None:
    config = _whisper_config().model_copy(update={"provider": "deepgram"})

    with pytest.raises(ASRError):
        build_asr_backend(config)


async def test_mock_backend_records_chunks_and_fires_callbacks() -> None:
    backend = MockASRBackend()
    partials: list[str] = []
    finals: list[str] = []
    backend.on_partial(partials.append)
    backend.on_final(finals.append)

    await backend.start_stream()
    await backend.push_audio(b"chunk-a")
    await backend.push_audio(b"chunk-b")
    backend.emit_partial("正在识别")
    backend.emit_final("最终结果")
    await backend.stop_stream()

    assert backend.pushed_chunks == [b"chunk-a", b"chunk-b"]
    assert partials == ["正在识别"]
    assert finals == ["最终结果"]


async def test_whisper_backend_rejects_push_before_start() -> None:
    backend = WhisperASRBackend(_whisper_config())

    with pytest.raises(ASRError):
        await backend.push_audio(b"anything")


async def test_whisper_backend_double_start_raises() -> None:
    backend = WhisperASRBackend(_whisper_config())
    await backend.start_stream()

    with pytest.raises(ASRError):
        await backend.start_stream()


async def test_whisper_backend_empty_buffer_is_noop_on_stop() -> None:
    backend = WhisperASRBackend(_whisper_config())
    finals: list[str] = []
    backend.on_final(finals.append)

    await backend.start_stream()
    await backend.stop_stream()  # no push_audio; nothing to transcribe

    assert finals == []


async def test_whisper_backend_transcribes_and_fires_final(monkeypatch) -> None:
    """Happy path: start -> push 2 chunks -> stop. We monkeypatch the
    decode + transcribe helpers so the test doesn't need ffmpeg or the
    real whisper model on disk."""
    backend = WhisperASRBackend(_whisper_config())
    finals: list[str] = []
    backend.on_final(finals.append)

    def fake_decode_and_transcribe(self, audio_bytes: bytes) -> str:
        assert audio_bytes == b"chunk-achunk-b"
        return "这是模拟转写结果"

    monkeypatch.setattr(
        WhisperASRBackend, "_decode_and_transcribe", fake_decode_and_transcribe
    )

    await backend.start_stream()
    await backend.push_audio(b"chunk-a")
    await backend.push_audio(b"chunk-b")
    await backend.stop_stream()

    assert finals == ["这是模拟转写结果"]


async def test_whisper_backend_wraps_decode_failure_as_asr_error(monkeypatch) -> None:
    backend = WhisperASRBackend(_whisper_config())
    finals: list[str] = []
    backend.on_final(finals.append)

    def bomb(self, audio_bytes: bytes) -> str:
        raise RuntimeError("decoder exploded")

    monkeypatch.setattr(WhisperASRBackend, "_decode_and_transcribe", bomb)

    await backend.start_stream()
    await backend.push_audio(b"junk")

    with pytest.raises(ASRError):
        await backend.stop_stream()
    assert finals == []


async def test_whisper_backend_surfaces_unsupported_audio(monkeypatch) -> None:
    backend = WhisperASRBackend(_whisper_config())

    def raise_unsupported(self, audio_bytes: bytes) -> str:
        raise ASRUnsupportedAudioError("not a valid audio container")

    monkeypatch.setattr(WhisperASRBackend, "_decode_and_transcribe", raise_unsupported)

    await backend.start_stream()
    await backend.push_audio(b"not-actually-audio")

    with pytest.raises(ASRUnsupportedAudioError):
        await backend.stop_stream()


def test_no_azure_key_strings_leak_in_source() -> None:
    """Meta-test: `subscription_key` / `AZURE_SPEECH_KEY` references must not
    re-appear anywhere under app/. The Azure swap-out left sentry's redaction
    rule list alone (forward-compat for future API providers) — that file is
    the one allowed exception."""
    root = pathlib.Path(__file__).resolve().parents[2] / "app"
    allowed_paths = {
        root / "infra" / "observability" / "sentry.py",
    }
    offenders: list[str] = []
    for path in root.rglob("*.py"):
        if path in allowed_paths:
            continue
        text = path.read_text(encoding="utf-8")
        if "subscription_key" in text or "AZURE_SPEECH_KEY" in text:
            offenders.append(str(path.relative_to(root)))
    assert not offenders, f"secret-key strings leaked to: {offenders}"
