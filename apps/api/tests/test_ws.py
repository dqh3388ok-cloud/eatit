from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient

from app.api.dependencies.auth import AuthenticatedUser, MOCK_USER_EMAIL, MOCK_USER_ID
from app.main import app


class _FakeResult:
    def __init__(self, value: object) -> None:
        self._value = value

    def scalar_one_or_none(self) -> object:
        return self._value


class _FakeSession:
    async def execute(self, *_args, **_kwargs) -> _FakeResult:
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

    async def __aenter__(self) -> "_FakeSession":
        return self

    async def __aexit__(self, *_args) -> None:
        return None


def _fake_session_factory() -> _FakeSession:
    return _FakeSession()


async def _fake_get_websocket_user(*_args, **_kwargs) -> AuthenticatedUser:
    return AuthenticatedUser(id=MOCK_USER_ID, email=MOCK_USER_EMAIL)


def test_websocket_text_event_returns_not_implemented(monkeypatch) -> None:
    from app.ws import endpoint as ws_endpoint

    monkeypatch.setattr(ws_endpoint, "AsyncSessionFactory", _fake_session_factory)
    monkeypatch.setattr(ws_endpoint, "get_websocket_user", _fake_get_websocket_user)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock") as websocket:
            websocket.send_json({"event": "client.session.pause"})
            response = websocket.receive_json()

    assert response == {
        "event": "server.error",
        "code": "not_implemented",
        "message": "Websocket event client.session.pause is defined but not implemented in phase 2.",
        "recoverable": True,
    }


def test_websocket_binary_event_returns_not_implemented(monkeypatch) -> None:
    from app.ws import endpoint as ws_endpoint

    monkeypatch.setattr(ws_endpoint, "AsyncSessionFactory", _fake_session_factory)
    monkeypatch.setattr(ws_endpoint, "get_websocket_user", _fake_get_websocket_user)

    with TestClient(app) as client:
        with client.websocket_connect("/ws/sessions/01964b52-1a8d-7b10-8d75-f0d4c7f00020?token=mock") as websocket:
            websocket.send_bytes(b"audio-chunk")
            response = websocket.receive_json()

    assert response == {
        "event": "server.error",
        "code": "not_implemented",
        "message": "Binary audio frames are reserved for ASR integration in a later phase.",
        "recoverable": True,
    }
