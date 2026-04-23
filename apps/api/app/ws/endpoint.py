"""WebSocket endpoint for a single interview session.

Protocol (phase3-constraints.md §A2):
1. Client connects; the server accepts and validates the session owner.
2. First text frame MUST be `client.session.init` carrying the BYOK
   LLMConfig. Any other first frame -> `server.error{code:"session_not_initialized"}`
   + close with 1008 policy violation.
3. Subsequent text frames drive the orchestrator:
   - `client.turn.end{question, answer, turn_index}` -> SessionRuntime.run_turn
     then drain the runtime's outbound event queue and forward to the client.
   - `client.session.end` -> close gracefully.
4. On disconnect (clean or not) the runtime's `on_session_end()` runs
   from a `finally` block so the LLMConfig is released regardless of
   path.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from pydantic import ValidationError
from sqlalchemy import select

from app.api.dependencies.auth import get_websocket_user
from app.infra.db.session import AsyncSessionFactory
from app.models.session import DirectionFramework, InterviewSession
from app.orchestrator.events import (
    QuestionGeneratedEvent,
    ReferenceAnswerReadyEvent,
    TurnAssessedEvent,
    TurnCompressedEvent,
)
from app.orchestrator.runtime import SessionRuntime
from app.ws.manager import socket_manager
from app.ws.schemas import (
    CLIENT_TEXT_EVENT_ADAPTER,
    ClientSessionEndEvent,
    ClientSessionInitEvent,
    ClientTurnEndEvent,
)


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
                InterviewSession.id == str(session_id),
                InterviewSession.user_id == current_user.id,
            )
        )
        interview_session = result.scalar_one_or_none()
        if interview_session is None:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        framework_json = await _load_framework_json(session, str(session_id))

    await socket_manager.connect(session_id, websocket)
    runtime: SessionRuntime | None = None

    try:
        # --- First-frame protocol ---
        first_frame = await _receive_first_frame(websocket)
        if first_frame is None:
            return

        try:
            parsed_first = CLIENT_TEXT_EVENT_ADAPTER.validate_python(first_frame)
        except ValidationError:
            await _send_not_initialized(websocket)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        if not isinstance(parsed_first, ClientSessionInitEvent):
            await _send_not_initialized(websocket)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        runtime = SessionRuntime(
            session_id=str(session_id),
            llm_config=parsed_first.config,
        )

        # Bootstrap turn 0 so the candidate actually sees a question.
        # The turn_graph handles turn N>0 (assess previous answer, then
        # pick the next question); at turn 0 there is no previous answer,
        # so we call the interviewer directly with an empty history.
        try:
            await runtime.bootstrap_first_question(framework_json=framework_json)
        except Exception as exc:  # noqa: BLE001 — surface any agent failure
            await socket_manager.send_error(
                websocket,
                code="bootstrap_failed",
                message=f"无法生成首题:{exc}",
                recoverable=False,
            )
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR)
            return
        await _drain_queue(websocket, runtime)

        # --- Main loop ---
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"] is not None:
                await socket_manager.send_error(
                    websocket,
                    code="audio_unsupported",
                    message="Binary audio frames are reserved for ASR integration in a later phase.",
                    recoverable=True,
                )
                continue

            text = message.get("text")
            if text is None:
                continue

            try:
                payload = json.loads(text)
            except json.JSONDecodeError:
                await websocket.close(code=status.WS_1003_UNSUPPORTED_DATA)
                break

            try:
                parsed = CLIENT_TEXT_EVENT_ADAPTER.validate_python(payload)
            except ValidationError:
                await socket_manager.send_error(
                    websocket,
                    code="invalid_event",
                    message=f"Unsupported websocket event: {payload.get('event')}",
                    recoverable=True,
                )
                continue

            if isinstance(parsed, ClientTurnEndEvent):
                await runtime.run_turn(
                    turn_index=parsed.turn_index,
                    question=parsed.question,
                    answer=parsed.answer,
                    framework_json=framework_json,
                )
                await _drain_queue(websocket, runtime)
                continue

            if isinstance(parsed, ClientSessionEndEvent):
                break

            # Re-sent init / pause / resume events are acknowledged
            # silently in Phase 3.
            continue
    except WebSocketDisconnect:
        pass
    finally:
        if runtime is not None:
            # Give any ref-answer task a short window so its event
            # lands before we shut down the queue.
            await _drain_queue(websocket, runtime, deadline_s=0.2)
            await runtime.on_session_end()
        socket_manager.disconnect(session_id, websocket)


async def _receive_first_frame(websocket: WebSocket) -> Any | None:
    message = await websocket.receive()
    if message["type"] == "websocket.disconnect":
        return None
    if "bytes" in message and message["bytes"] is not None:
        await _send_not_initialized(websocket)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None
    text = message.get("text")
    if text is None:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        await _send_not_initialized(websocket)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return None


async def _send_not_initialized(websocket: WebSocket) -> None:
    await socket_manager.send_error(
        websocket,
        code="session_not_initialized",
        message="First frame must be client.session.init.",
        recoverable=False,
    )


async def _load_framework_json(session, interview_session_id: str) -> str:
    result = await session.execute(
        select(DirectionFramework).where(
            DirectionFramework.interview_session_id == interview_session_id
        )
    )
    row = result.scalar_one_or_none()
    if row is None or not isinstance(row.payload, dict):
        return "{}"
    agent_payload = row.payload.get("agent") if "agent" in row.payload else row.payload
    return json.dumps(agent_payload, ensure_ascii=False)


async def _drain_queue(
    websocket: WebSocket,
    runtime: SessionRuntime,
    deadline_s: float = 0.0,
) -> None:
    loop = asyncio.get_event_loop()
    end = loop.time() + deadline_s

    while True:
        try:
            event = runtime.event_queue.get_nowait()
        except asyncio.QueueEmpty:
            if deadline_s and loop.time() < end:
                await asyncio.sleep(0.02)
                continue
            return
        await websocket.send_json(_serialize_event(event))


def _serialize_event(event: object) -> dict[str, Any]:
    if isinstance(event, TurnAssessedEvent):
        return {
            "event": "server.turn.assessed",
            "payload": {
                "turn_index": event.turn_index,
                "summary": event.summary,
                "strengths": list(event.strengths),
                "weaknesses": list(event.weaknesses),
            },
        }
    if isinstance(event, TurnCompressedEvent):
        return {
            "event": "server.turn.compressed",
            "payload": {
                "summary": event.summary,
                "preserved_keywords": list(event.preserved_keywords),
                "open_threads": list(event.open_threads),
            },
        }
    if isinstance(event, QuestionGeneratedEvent):
        return {
            "event": "server.question.generated",
            "payload": {
                "turn_index": event.turn_index,
                "question": event.question,
                "intent": event.intent,
                "expected_depth": event.expected_depth,
                "followup_hint": event.followup_hint,
                "should_end": event.should_end,
            },
        }
    if isinstance(event, ReferenceAnswerReadyEvent):
        return {
            "event": "server.reference.ready",
            "payload": {
                "turn_index": event.turn_index,
                "answer_outline": list(event.answer_outline),
                "ideal_answer": event.ideal_answer,
                "key_evaluation_points": list(event.key_evaluation_points),
                "common_pitfalls": list(event.common_pitfalls),
            },
        }
    return {
        "event": "server.error",
        "code": "unknown_event",
        "message": "",
        "recoverable": True,
    }
