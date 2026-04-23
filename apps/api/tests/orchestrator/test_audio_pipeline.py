from __future__ import annotations

import asyncio
import gc
import weakref

import pytest
from pydantic import SecretStr

from app.infra.asr import MockASRBackend
from app.infra.llm.config import LLMConfig
from app.orchestrator.events import TranscriptFinalEvent
from app.orchestrator.runtime import SessionRuntime


@pytest.fixture
def config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        api_key=SecretStr("sk-audio-pipeline-test"),
        model="gpt-4o-mini",
        base_url=None,
    )


class _TrailingFinalBackend(MockASRBackend):
    """Mock ASR backend that emits a final transcript inside `stop_stream` —
    a faithful stand-in for Azure's trailing `Recognized` behavior."""

    def __init__(self, final_text: str = "mock-final") -> None:
        super().__init__()
        self._final_text = final_text

    async def stop_stream(self) -> None:
        await super().stop_stream()
        text = self._final_text if self.pushed_chunks else ""
        self.emit_final(text)


async def test_start_push_stop_emits_final_and_stores_answer(config: LLMConfig) -> None:
    runtime = SessionRuntime(session_id="audio-turn-happy", llm_config=config)
    backend = _TrailingFinalBackend(final_text="你好世界")

    await runtime.start_audio_turn(turn_index=1, backend_factory=lambda: backend)
    await runtime.push_audio(b"chunk-a")
    await runtime.push_audio(b"chunk-b")
    final_text = await runtime.stop_audio_turn()

    assert final_text == "你好世界"
    assert runtime.get_audio_answer(1) == "你好世界"
    assert backend.stopped is True
    assert backend.pushed_chunks == [b"chunk-a", b"chunk-b"]

    # Drain event queue and verify a TranscriptFinalEvent was enqueued for
    # this turn.
    events = []
    while not runtime.event_queue.empty():
        events.append(runtime.event_queue.get_nowait())
    finals = [e for e in events if isinstance(e, TranscriptFinalEvent)]
    assert finals == [TranscriptFinalEvent(turn_index=1, text="你好世界")]

    await runtime.on_session_end()


async def test_on_session_end_stops_running_asr_backend(config: LLMConfig) -> None:
    runtime = SessionRuntime(session_id="audio-turn-cleanup", llm_config=config)
    backend = MockASRBackend()

    await runtime.start_audio_turn(turn_index=1, backend_factory=lambda: backend)
    # No explicit stop — the session ends mid-recording.
    await runtime.on_session_end()

    assert backend.stopped is True
    assert runtime._asr_backend is None
    assert runtime._last_final_by_turn == {}
    assert runtime._pending_final_events == {}


async def test_on_session_end_releases_asr_backend_via_weakref(config: LLMConfig) -> None:
    runtime = SessionRuntime(session_id="audio-turn-weakref", llm_config=config)

    backend_ref: weakref.ref[MockASRBackend] = weakref.ref(MockASRBackend())

    def _factory() -> MockASRBackend:
        # Build a fresh backend here so no local strong reference survives
        # outside the runtime once start_audio_turn returns.
        backend = MockASRBackend()
        nonlocal backend_ref
        backend_ref = weakref.ref(backend)
        return backend

    await runtime.start_audio_turn(turn_index=1, backend_factory=_factory)

    await runtime.on_session_end()
    gc.collect()

    assert backend_ref() is None, (
        "ASRBackend still reachable after on_session_end + gc.collect()"
    )


async def test_consecutive_audio_turns_do_not_leak_final_text(config: LLMConfig) -> None:
    runtime = SessionRuntime(session_id="audio-turn-sequence", llm_config=config)

    turn1_backend = _TrailingFinalBackend(final_text="答案A")
    await runtime.start_audio_turn(turn_index=1, backend_factory=lambda: turn1_backend)
    await runtime.push_audio(b"turn1-audio")
    assert await runtime.stop_audio_turn() == "答案A"

    turn2_backend = _TrailingFinalBackend(final_text="答案B")
    await runtime.start_audio_turn(turn_index=2, backend_factory=lambda: turn2_backend)
    await runtime.push_audio(b"turn2-audio")
    assert await runtime.stop_audio_turn() == "答案B"

    assert runtime.get_audio_answer(1) == "答案A"
    assert runtime.get_audio_answer(2) == "答案B"
    # A never-started turn has no stored final.
    assert runtime.get_audio_answer(99) is None

    await runtime.on_session_end()


async def test_stop_audio_turn_times_out_gracefully_when_no_final_arrives(
    config: LLMConfig,
) -> None:
    """If the backend never emits a final (SDK flake), stop_audio_turn must
    still return within the configured timeout rather than hang forever."""
    runtime = SessionRuntime(session_id="audio-turn-timeout", llm_config=config)
    backend = MockASRBackend()  # stop_stream does NOT emit final

    await runtime.start_audio_turn(turn_index=1, backend_factory=lambda: backend)
    await runtime.push_audio(b"no-final-coming")

    start = asyncio.get_event_loop().time()
    final_text = await runtime.stop_audio_turn(trailing_final_timeout=0.1)
    elapsed = asyncio.get_event_loop().time() - start

    assert final_text == ""
    assert runtime.get_audio_answer(1) is None
    assert elapsed < 1.0

    await runtime.on_session_end()
