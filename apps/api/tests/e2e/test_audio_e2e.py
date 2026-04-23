"""Phase 4 voice-mode end-to-end smoke.

Drives a single voice turn through the real WS handler + SessionRuntime
+ turn_graph with a mock ASR backend and patched LLM services:

    session.init
      -> server.question.generated (bootstrap turn 0)
      -> client.audio.start{turn_index: 1}
      -> 3 × binary audio chunks
      -> client.audio.stop{turn_index: 1}
      -> server.transcript.final
      -> client.turn.end{turn_index: 1, answer: ""}   ← voice mode, empty
      -> server.turn.assessed + server.turn.compressed + server.question.generated
      -> client.session.end

The turn.end's client-side `answer` is intentionally empty to verify the
WS endpoint falls back to `runtime.get_audio_answer(turn_index)` (the
ASR final transcript) when the turn was opened via audio.start.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi.testclient import TestClient

from app.agents.compression.schemas import CompressionAgentOutput
from app.agents.compression.service import CompressionAgentService
from app.agents.interviewer.schemas import InterviewerAgentOutput
from app.agents.interviewer.service import InterviewerAgentService
from app.agents.reference.schemas import ReferenceAgentOutput
from app.agents.reference.service import ReferenceAgentService
from app.api.dependencies.auth import (
    AuthenticatedUser,
    MOCK_USER_EMAIL,
    MOCK_USER_ID,
    get_websocket_user,
)
from app.infra.asr import MockASRBackend
from app.main import app
from app.orchestrator import turn_graph as turn_graph_mod
from app.orchestrator.state import TurnAssessment
from app.ws import endpoint as ws_endpoint


_VALID_CONFIG_PAYLOAD = {
    "provider": "openai",
    "api_key": "sk-audio-e2e",
    "model": "gpt-4o-mini",
    "base_url": None,
}


class _EndpointingBackend(MockASRBackend):
    """Mock backend that, like Azure, emits a final transcript during
    `stop_stream`. The test captures the audio answer this way."""

    def __init__(self, final_text: str) -> None:
        super().__init__()
        self._final_text = final_text

    async def stop_stream(self) -> None:
        await super().stop_stream()
        text = self._final_text if self.pushed_chunks else ""
        self.emit_final(text)


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    """Returns a matching InterviewSession on the first execute call and
    None on the second (direction-framework lookup). Mirrors test_ws.py."""

    def __init__(self, session_id: UUID) -> None:
        self._session_id = session_id
        self._calls = 0

    async def execute(self, *_args: Any, **_kwargs: Any) -> _FakeResult:
        self._calls += 1
        if self._calls == 1:
            return _FakeResult(
                type(
                    "InterviewSessionStub",
                    (),
                    {"id": self._session_id, "user_id": MOCK_USER_ID},
                )()
            )
        return _FakeResult(None)

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_args: Any) -> None:
        return None


async def _fake_ws_user(*_args: Any, **_kwargs: Any) -> AuthenticatedUser:
    return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)


def test_voice_turn_round_trip_with_mock_asr_and_mock_llm(monkeypatch) -> None:
    session_uuid = UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00020")
    audio_final_text = "我当时选择了完成率作为北极星指标。"

    captured_answer: dict[str, str | None] = {"value": None}

    async def fake_interviewer_run(_self, _input, _gateway):
        return InterviewerAgentOutput(
            question="请结合你最近一个上线项目展开讲讲。",
            intent="开场破冰",
            expected_depth="surface",
            followup_hint=None,
            should_end=False,
        )

    async def fake_reference_run(_self, _input, _gateway):
        return ReferenceAgentOutput(
            answer_outline=["先锁用户价值"],
            ideal_answer="参考答案略",
            key_evaluation_points=["是否能归因到模型改动"],
            common_pitfalls=["一上来就用 DAU"],
        )

    async def fake_compression_run(_self, _input, _gateway):
        return CompressionAgentOutput(
            summary="候选人展开了项目指标环节",
            preserved_keywords=["完成率"],
            open_threads=[],
        )

    async def fake_structured_completion(
        _client, *, messages, response_model, max_retries=2
    ):
        if response_model is TurnAssessment:
            # Capture the prompt text so we can assert the turn.end answer
            # was resolved from the ASR final rather than the (empty) client
            # payload.
            rendered = "\n".join(m.get("content", "") for m in messages)
            captured_answer["value"] = rendered
            return TurnAssessment(
                summary="回答结构清晰",
                strengths=["有量化"],
                weaknesses=[],
            )
        raise AssertionError(f"unexpected response_model: {response_model}")

    monkeypatch.setattr(InterviewerAgentService, "run", fake_interviewer_run)
    monkeypatch.setattr(ReferenceAgentService, "run", fake_reference_run)
    monkeypatch.setattr(CompressionAgentService, "run", fake_compression_run)
    monkeypatch.setattr(turn_graph_mod, "structured_completion", fake_structured_completion)

    monkeypatch.setattr(
        ws_endpoint, "AsyncSessionFactory", lambda: _FakeSession(session_uuid)
    )
    monkeypatch.setattr(ws_endpoint, "get_websocket_user", _fake_ws_user)
    app.dependency_overrides[get_websocket_user] = _fake_ws_user

    mock_backends: list[_EndpointingBackend] = []

    def _asr_factory() -> _EndpointingBackend:
        backend = _EndpointingBackend(final_text=audio_final_text)
        mock_backends.append(backend)
        return backend

    monkeypatch.setattr(ws_endpoint, "asr_backend_factory", _asr_factory)

    try:
        with TestClient(app) as client:
            with client.websocket_connect(
                f"/ws/sessions/{session_uuid}?token=mock"
            ) as ws:
                # 1) session.init + drain bootstrap question.
                ws.send_json({"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD})
                bootstrap = ws.receive_json()
                assert bootstrap["event"] == "server.question.generated"
                assert bootstrap["payload"]["turn_index"] == 0

                # 2) audio.start + 3 binary chunks + audio.stop.
                ws.send_json({"event": "client.audio.start", "turn_index": 1})
                ws.send_bytes(b"opus-chunk-1")
                ws.send_bytes(b"opus-chunk-2")
                ws.send_bytes(b"opus-chunk-3")
                ws.send_json({"event": "client.audio.stop", "turn_index": 1})

                # 3) server.transcript.final.
                transcript = ws.receive_json()
                assert transcript == {
                    "event": "server.transcript.final",
                    "payload": {"turn_index": 1, "text": audio_final_text},
                }

                # 4) turn.end with empty client answer — voice mode should
                # make the WS handler resolve the answer via
                # runtime.get_audio_answer(1).
                ws.send_json(
                    {
                        "event": "client.turn.end",
                        "turn_index": 1,
                        "question": bootstrap["payload"]["question"],
                        "answer": "",
                    }
                )

                # 5) Drain up to 5 outbound events and assert the trio
                # arrived. reference.ready may interleave so take a loose
                # window.
                needed = {
                    "server.turn.assessed",
                    "server.turn.compressed",
                    "server.question.generated",
                }
                seen: set[str] = set()
                for _ in range(5):
                    event = ws.receive_json()
                    name = event["event"]
                    if name in needed:
                        seen.add(name)
                    if seen == needed:
                        break

                assert seen == needed
                ws.send_json({"event": "client.session.end"})
    finally:
        app.dependency_overrides.pop(get_websocket_user, None)

    # Exactly one ASR backend was constructed for the single audio turn.
    assert len(mock_backends) == 1
    assert mock_backends[0].pushed_chunks == [
        b"opus-chunk-1",
        b"opus-chunk-2",
        b"opus-chunk-3",
    ]

    # The turn_assessment prompt must have carried the ASR final text as
    # the answer — i.e. the voice-mode answer resolution worked. The
    # captured messages include both system + user; we search the whole
    # rendered blob for the final_text substring.
    rendered = captured_answer["value"] or ""
    assert audio_final_text in rendered, (
        "turn_assessment did not see the ASR final transcript as the answer"
    )
