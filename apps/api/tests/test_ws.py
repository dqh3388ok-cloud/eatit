from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies.auth import AuthenticatedUser, MOCK_USER_EMAIL, MOCK_USER_ID
from app.main import app


_VALID_CONFIG_PAYLOAD = {
    "provider": "openai",
    "api_key": "sk-ws-test",
    "model": "gpt-4o-mini",
    "base_url": None,
}


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    """Returns a stub session for the owner check and a None row for the
    direction-framework lookup (the second execute call). That keeps the
    test DB-free while still exercising the real handler code path."""

    def __init__(self) -> None:
        self._call = 0

    async def execute(self, *_args, **_kwargs) -> _FakeResult:
        self._call += 1
        if self._call == 1:
            return _FakeResult(
                type(
                    "InterviewSessionStub",
                    (),
                    {
                        "id": UUID("01964b52-1a8d-7b10-8d75-f0d4c7f00020"),
                        "user_id": MOCK_USER_ID,
                    },
                )()
            )
        return _FakeResult(None)

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_args) -> None:
        return None


def _fake_session_factory() -> _FakeSession:
    return _FakeSession()


async def _fake_get_websocket_user(*_args, **_kwargs) -> AuthenticatedUser:
    return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)


def _patch_ws_deps(monkeypatch) -> None:
    from app.ws import endpoint as ws_endpoint

    monkeypatch.setattr(ws_endpoint, "AsyncSessionFactory", _fake_session_factory)
    monkeypatch.setattr(ws_endpoint, "get_websocket_user", _fake_get_websocket_user)


def test_websocket_rejects_wrong_first_event(monkeypatch) -> None:
    """Any non-`client.session.init` first frame must get a typed error
    and a 1008 close per phase3-constraints.md §A2."""
    _patch_ws_deps(monkeypatch)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json({"event": "client.session.pause"})
            response = websocket.receive_json()

    assert response["event"] == "server.error"
    assert response["code"] == "session_not_initialized"
    assert response["recoverable"] is False


def test_websocket_rejects_binary_first_frame(monkeypatch) -> None:
    """Binary first frames are also rejected — the protocol is strict."""
    _patch_ws_deps(monkeypatch)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_bytes(b"binary-before-init")
            response = websocket.receive_json()

    assert response["event"] == "server.error"
    assert response["code"] == "session_not_initialized"


def test_websocket_accepts_session_init_then_turn(monkeypatch) -> None:
    """Happy path: init -> turn.end emits three server events in any order."""
    from app.agents.compression.schemas import CompressionAgentOutput
    from app.agents.compression.service import CompressionAgentService
    from app.agents.interviewer.schemas import InterviewerAgentOutput
    from app.agents.interviewer.service import InterviewerAgentService
    from app.agents.reference.schemas import ReferenceAgentOutput
    from app.agents.reference.service import ReferenceAgentService
    from app.orchestrator import turn_graph as turn_graph_mod
    from app.orchestrator.state import TurnAssessment

    _patch_ws_deps(monkeypatch)

    async def fake_interviewer_run(self, input, gateway):  # noqa: ANN001
        return InterviewerAgentOutput(
            question="你怎么衡量这个指标?",
            intent="考察深度",
            expected_depth="tactical",
            followup_hint=None,
            should_end=False,
        )

    async def fake_reference_run(self, input, gateway):  # noqa: ANN001
        return ReferenceAgentOutput(
            answer_outline=["先锁用户价值"],
            ideal_answer="参考答案略。",
            key_evaluation_points=["是否能归因"],
            common_pitfalls=["一上来就用 DAU"],
        )

    async def fake_compression_run(self, input, gateway):  # noqa: ANN001
        return CompressionAgentOutput(
            summary="压缩摘要占位",
            preserved_keywords=["北极星"],
            open_threads=[],
        )

    async def fake_structured_completion(
        client, *, messages, response_model, max_retries=2
    ):  # noqa: ANN001
        if response_model is TurnAssessment:
            return TurnAssessment(summary="回答清晰", strengths=["结构好"], weaknesses=[])
        raise AssertionError(f"unexpected structured_completion model: {response_model}")

    monkeypatch.setattr(InterviewerAgentService, "run", fake_interviewer_run)
    monkeypatch.setattr(ReferenceAgentService, "run", fake_reference_run)
    monkeypatch.setattr(CompressionAgentService, "run", fake_compression_run)
    monkeypatch.setattr(turn_graph_mod, "structured_completion", fake_structured_completion)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json(
                {"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD}
            )
            websocket.send_json(
                {
                    "event": "client.turn.end",
                    "turn_index": 1,
                    "question": "北极星指标怎么选?",
                    "answer": "我们选了完成率。",
                }
            )

            events: list[dict] = []
            for _ in range(3):
                events.append(websocket.receive_json())

            websocket.send_json({"event": "client.session.end"})

    event_names = {e["event"] for e in events}
    assert "server.turn.assessed" in event_names
    assert "server.turn.compressed" in event_names
    assert "server.question.generated" in event_names


def _patch_bootstrap(monkeypatch) -> None:
    """Stub the InterviewerAgent so session.init returns a bootstrap question
    without calling LiteLLM."""
    from app.agents.interviewer.schemas import InterviewerAgentOutput
    from app.agents.interviewer.service import InterviewerAgentService

    async def fake_interviewer_run(_self, _input, _gateway):
        return InterviewerAgentOutput(
            question="起个手,介绍一下你自己。",
            intent="暖场",
            expected_depth="surface",
        )

    monkeypatch.setattr(InterviewerAgentService, "run", fake_interviewer_run)


class _FakeAsrBackend:
    """Synchronous stand-in for ASRBackend used by the WS tests.

    Records pushed chunks and, on `stop_stream`, synchronously fires the final
    callback — simulating Azure's trailing `Recognized` event without the
    real SDK. Runtime's registered callback uses `loop.call_soon_threadsafe`
    so the enqueued final event lands on the event queue during the
    `await asyncio.sleep(0)` inside `stop_audio_turn`.
    """

    def __init__(self, final_text: str = "mock-transcript") -> None:
        self.pushed_chunks: list[bytes] = []
        self._partial_callbacks: list = []
        self._final_callbacks: list = []
        self._final_text = final_text
        self.started = False
        self.stopped = False

    def on_partial(self, callback) -> None:
        self._partial_callbacks.append(callback)

    def on_final(self, callback) -> None:
        self._final_callbacks.append(callback)

    async def start_stream(self) -> None:
        self.started = True

    async def push_audio(self, chunk: bytes) -> None:
        self.pushed_chunks.append(chunk)

    async def stop_stream(self) -> None:
        self.stopped = True
        text = self._final_text if self.pushed_chunks else ""
        for cb in self._final_callbacks:
            cb(text)


def test_websocket_binary_frame_without_audio_start_errors_and_continues(monkeypatch) -> None:
    """Binary frames before `client.audio.start` get `audio_not_started` and
    the connection stays open for a subsequent turn.end."""
    _patch_ws_deps(monkeypatch)
    _patch_bootstrap(monkeypatch)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json(
                {"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD}
            )
            bootstrap = websocket.receive_json()
            assert bootstrap["event"] == "server.question.generated"

            websocket.send_bytes(b"orphan-audio-chunk")
            response = websocket.receive_json()

            websocket.send_json({"event": "client.session.end"})

    assert response == {
        "event": "server.error",
        "code": "audio_not_started",
        "message": "Send client.audio.start before binary audio chunks.",
        "recoverable": True,
    }


def test_websocket_audio_start_chunks_stop_emits_final(monkeypatch) -> None:
    """Happy audio path: audio.start → 2 binary chunks → audio.stop →
    server.transcript.final with mock text."""
    from app.ws import endpoint as ws_endpoint

    _patch_ws_deps(monkeypatch)
    _patch_bootstrap(monkeypatch)

    backends: list[_FakeAsrBackend] = []

    def _fake_factory() -> _FakeAsrBackend:
        backend = _FakeAsrBackend(final_text="你好世界")
        backends.append(backend)
        return backend

    monkeypatch.setattr(ws_endpoint, "asr_backend_factory", _fake_factory)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json(
                {"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD}
            )
            bootstrap = websocket.receive_json()
            assert bootstrap["event"] == "server.question.generated"

            websocket.send_json({"event": "client.audio.start", "turn_index": 1})
            websocket.send_bytes(b"chunk-1")
            websocket.send_bytes(b"chunk-2")
            websocket.send_json({"event": "client.audio.stop", "turn_index": 1})

            final_event = websocket.receive_json()

            websocket.send_json({"event": "client.session.end"})

    assert len(backends) == 1
    assert backends[0].pushed_chunks == [b"chunk-1", b"chunk-2"]
    assert backends[0].stopped is True
    assert final_event == {
        "event": "server.transcript.final",
        "payload": {"turn_index": 1, "text": "你好世界"},
    }


def test_websocket_audio_start_stop_without_chunks_emits_empty_final(monkeypatch) -> None:
    """audio.start → audio.stop with no chunks in between must not crash;
    the final transcript is the empty string."""
    from app.ws import endpoint as ws_endpoint

    _patch_ws_deps(monkeypatch)
    _patch_bootstrap(monkeypatch)

    def _fake_factory() -> _FakeAsrBackend:
        return _FakeAsrBackend(final_text="should-not-appear")

    monkeypatch.setattr(ws_endpoint, "asr_backend_factory", _fake_factory)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json(
                {"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD}
            )
            bootstrap = websocket.receive_json()
            assert bootstrap["event"] == "server.question.generated"

            websocket.send_json({"event": "client.audio.start", "turn_index": 1})
            websocket.send_json({"event": "client.audio.stop", "turn_index": 1})

            final_event = websocket.receive_json()

            websocket.send_json({"event": "client.session.end"})

    assert final_event == {
        "event": "server.transcript.final",
        "payload": {"turn_index": 1, "text": ""},
    }


def test_websocket_double_audio_start_emits_already_started(monkeypatch) -> None:
    """A second `client.audio.start` without an intervening `audio.stop` is
    rejected with `audio_already_started` and the first session is unaffected."""
    from app.ws import endpoint as ws_endpoint

    _patch_ws_deps(monkeypatch)
    _patch_bootstrap(monkeypatch)

    backends: list[_FakeAsrBackend] = []

    def _fake_factory() -> _FakeAsrBackend:
        backend = _FakeAsrBackend()
        backends.append(backend)
        return backend

    monkeypatch.setattr(ws_endpoint, "asr_backend_factory", _fake_factory)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json(
                {"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD}
            )
            bootstrap = websocket.receive_json()
            assert bootstrap["event"] == "server.question.generated"

            websocket.send_json({"event": "client.audio.start", "turn_index": 1})
            websocket.send_json({"event": "client.audio.start", "turn_index": 1})

            response = websocket.receive_json()

            websocket.send_json({"event": "client.audio.stop", "turn_index": 1})
            websocket.receive_json()  # drain the final emitted by audio.stop
            websocket.send_json({"event": "client.session.end"})

    assert response == {
        "event": "server.error",
        "code": "audio_already_started",
        "message": "An audio turn is already in progress.",
        "recoverable": True,
    }
    # The second start never reached the factory — only one backend was built.
    assert len(backends) == 1
