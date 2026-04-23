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


def test_websocket_binary_event_after_init(monkeypatch) -> None:
    """Binary mid-session frames still get `not_implemented` (unchanged)."""
    _patch_ws_deps(monkeypatch)

    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock"
        ) as websocket:
            websocket.send_json(
                {"event": "client.session.init", "config": _VALID_CONFIG_PAYLOAD}
            )
            websocket.send_bytes(b"audio-chunk")
            response = websocket.receive_json()

    assert response == {
        "event": "server.error",
        "code": "audio_unsupported",
        "message": "Binary audio frames are reserved for ASR integration in a later phase.",
        "recoverable": True,
    }
