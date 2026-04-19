from __future__ import annotations

from collections import defaultdict
from uuid import UUID

from fastapi import WebSocket

from app.ws.schemas import ServerErrorEvent


class SessionSocketManager:
    def __init__(self) -> None:
        self._connections: dict[UUID, set[WebSocket]] = defaultdict(set)

    async def connect(self, session_id: UUID, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id].add(websocket)

    def disconnect(self, session_id: UUID, websocket: WebSocket) -> None:
        connections = self._connections.get(session_id)
        if connections is None:
            return
        connections.discard(websocket)
        if not connections:
            self._connections.pop(session_id, None)

    async def send_error(
        self,
        websocket: WebSocket,
        *,
        code: str,
        message: str,
        recoverable: bool,
    ) -> None:
        event = ServerErrorEvent(
            event="server.error",
            code=code,
            message=message,
            recoverable=recoverable,
        )
        await websocket.send_json(event.model_dump(mode="json"))


socket_manager = SessionSocketManager()
