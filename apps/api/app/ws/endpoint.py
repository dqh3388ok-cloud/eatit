from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.dependencies.auth import get_websocket_user
from app.infra.db.session import AsyncSessionFactory
from app.models.session import InterviewSession
from app.ws.manager import socket_manager
from app.ws.schemas import CLIENT_TEXT_EVENT_ADAPTER


router = APIRouter()


@router.websocket("/ws/sessions/{session_id}")
async def interview_socket(websocket: WebSocket, session_id: UUID) -> None:
    token = websocket.query_params.get("token", "")

    async with AsyncSessionFactory() as session:
        try:
            current_user = await get_websocket_user(token, session)
        except ValueError:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        result = await session.execute(
            select(InterviewSession).where(
                InterviewSession.id == session_id,
                InterviewSession.user_id == current_user.id,
            )
        )
        interview_session = result.scalar_one_or_none()
        if interview_session is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await socket_manager.connect(session_id, websocket)

        try:
            while True:
                message = await websocket.receive()

                if message["type"] == "websocket.disconnect":
                    break

                if "bytes" in message and message["bytes"] is not None:
                    await socket_manager.send_error(
                        websocket,
                        code="not_implemented",
                        message="Binary audio frames are reserved for ASR integration in a later phase.",
                        recoverable=True,
                    )
                    continue

                if "text" in message and message["text"] is not None:
                    try:
                        payload = json.loads(message["text"])
                    except json.JSONDecodeError:
                        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                        break

                    event_name = payload.get("event")
                    if not isinstance(event_name, str):
                        await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                        break

                    try:
                        CLIENT_TEXT_EVENT_ADAPTER.validate_python(payload)
                    except ValidationError:
                        await socket_manager.send_error(
                            websocket,
                            code="invalid_event",
                            message=f"Unsupported websocket event: {event_name}",
                            recoverable=True,
                        )
                        continue

                    await socket_manager.send_error(
                        websocket,
                        code="not_implemented",
                        message=f"Websocket event {event_name} is defined but not implemented in phase 2.",
                        recoverable=True,
                    )
                    continue

                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                break
        except WebSocketDisconnect:
            pass
        finally:
            socket_manager.disconnect(session_id, websocket)
