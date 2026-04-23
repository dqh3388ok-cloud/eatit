from __future__ import annotations

import pathlib
from unittest.mock import MagicMock, patch

import azure.cognitiveservices.speech as speechsdk
import pytest

from app.infra.asr import (
    ASRAuthError,
    ASRConfig,
    AzureASRBackend,
    MockASRBackend,
    build_asr_backend,
)


SECRET_KEY = "sub-do-not-leak-a1b2"


def _azure_config(**overrides) -> ASRConfig:
    data = {"subscription_key": SECRET_KEY, "region": "eastasia"}
    data.update(overrides)
    return ASRConfig(**data)


def test_asr_config_repr_masks_subscription_key() -> None:
    config = _azure_config()

    assert SECRET_KEY not in repr(config)
    assert SECRET_KEY not in str(config)
    assert "***" in repr(config)
    # SecretStr masks on its own repr too
    assert SECRET_KEY not in repr(config.subscription_key)
    assert config.subscription_key.get_secret_value() == SECRET_KEY


def test_build_asr_backend_returns_azure_backend() -> None:
    backend = build_asr_backend(_azure_config())

    assert isinstance(backend, AzureASRBackend)


async def test_mock_backend_records_chunks_and_fires_callbacks() -> None:
    backend = MockASRBackend()
    partials: list[str] = []
    finals: list[str] = []
    backend.on_partial(partials.append)
    backend.on_final(finals.append)

    await backend.start_stream()
    await backend.push_audio(b"chunk-one")
    await backend.push_audio(b"chunk-two")
    backend.emit_partial("你好")
    backend.emit_final("你好,世界")
    await backend.stop_stream()

    assert backend.pushed_chunks == [b"chunk-one", b"chunk-two"]
    assert partials == ["你好"]
    assert finals == ["你好,世界"]
    assert backend.stopped is True


async def test_azure_backend_maps_recognizer_construction_failure_to_auth_error() -> None:
    backend = AzureASRBackend(_azure_config())

    with patch.object(
        speechsdk,
        "SpeechRecognizer",
        side_effect=Exception("Authentication failed: 401 invalid subscription"),
    ):
        with pytest.raises(ASRAuthError):
            await backend.start_stream()


async def test_azure_backend_stream_lifecycle_start_push_stop_completes() -> None:
    backend = AzureASRBackend(_azure_config())

    fake_stream = MagicMock(name="push_stream")
    fake_recognizer = MagicMock(name="recognizer")
    # Ensure start/stop async helpers resolve synchronously via .get()
    fake_recognizer.start_continuous_recognition_async.return_value = MagicMock()
    fake_recognizer.stop_continuous_recognition_async.return_value = MagicMock()

    with (
        patch.object(speechsdk, "SpeechConfig", return_value=MagicMock()),
        patch.object(speechsdk.audio, "AudioStreamFormat", return_value=MagicMock()),
        patch.object(speechsdk.audio, "PushAudioInputStream", return_value=fake_stream),
        patch.object(speechsdk.audio, "AudioConfig", return_value=MagicMock()),
        patch.object(speechsdk, "SpeechRecognizer", return_value=fake_recognizer),
    ):
        await backend.start_stream()
        await backend.push_audio(b"aaa")
        await backend.push_audio(b"bbb")
        await backend.push_audio(b"ccc")
        await backend.stop_stream()

    assert fake_stream.write.call_count == 3
    fake_stream.close.assert_called_once()
    fake_recognizer.start_continuous_recognition_async.assert_called_once()
    fake_recognizer.stop_continuous_recognition_async.assert_called_once()


def test_no_secret_token_leakage_in_app_tree() -> None:
    """Meta-test: `subscription_key` / `AZURE_SPEECH_KEY` references must live
    only inside the ASR infra package. Any other file that mentions them is a
    potential leak into logs, cache keys, or error responses."""

    app_dir = pathlib.Path(__file__).resolve().parents[2] / "app"
    allowed = {
        "infra/asr/config.py",
        "infra/asr/factory.py",
        "infra/asr/azure_backend.py",
    }
    hits: set[str] = set()
    for py in app_dir.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "subscription_key" in text or "AZURE_SPEECH_KEY" in text:
            rel = py.relative_to(app_dir).as_posix()
            hits.add(rel)

    unexpected = hits - allowed
    assert not unexpected, f"secret token leaked into: {sorted(unexpected)}"
