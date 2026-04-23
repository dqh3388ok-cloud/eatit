"""Session-scoped runtime for the orchestrator.

`SessionRuntime` owns everything that lives for the duration of one
WebSocket connection: the BYOK gateway, the compiled turn graph, the
outbound event queue, and the set of in-flight reference-answer tasks.

Key invariants (phase3-constraints.md §A3):
- `on_session_end()` must nil the held `LLMConfig` *and* every container
  that transitively references it (the gateway, the compiled graph).
  A test holds a weakref to the config and asserts it dies after
  `on_session_end() + gc.collect()`.
- All in-flight work is trackable and cancellable. Reference answers are
  fire-and-forget by design but registered in `_ref_answer_tasks` so
  `on_session_end()` can cancel them rather than leave them dangling.
- `on_session_end()` is invoked from WS close, explicit
  `client.session.end`, AND uncaught exceptions — it must therefore be
  idempotent.

`asyncio.TaskGroup` scopes the per-turn work so that a mid-turn
exception cancels sibling tasks without leaking.
"""

from __future__ import annotations

import asyncio
from typing import Any

from app.agents.reference.schemas import ReferenceAgentInput
from app.agents.reference.service import ReferenceAgentService
from app.infra.llm import LLMGateway, build_gateway
from app.infra.llm.config import LLMConfig
from app.orchestrator.events import (
    QuestionGeneratedEvent,
    ReferenceAnswerReadyEvent,
    TurnAssessedEvent,
    TurnCompressedEvent,
)
from app.orchestrator.state import TurnState
from app.orchestrator.turn_graph import build_turn_graph


class SessionClosedError(RuntimeError):
    """Raised when `run_turn` is called after `on_session_end`."""


class SessionRuntime:
    def __init__(self, session_id: str, llm_config: LLMConfig) -> None:
        self.session_id = session_id
        self._llm_config: LLMConfig | None = llm_config
        self._gateway: LLMGateway | None = build_gateway(llm_config)
        self._graph: Any | None = None
        self._task_group: asyncio.TaskGroup | None = None
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._ref_answer_tasks: set[asyncio.Task] = set()
        self._closed = False

    async def __aenter__(self) -> "SessionRuntime":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.on_session_end()

    @property
    def event_queue(self) -> asyncio.Queue:
        return self._event_queue

    async def run_turn(
        self,
        *,
        turn_index: int,
        question: str,
        answer: str,
        framework_json: str,
        recent_turns: list | None = None,
        previous_summary: str | None = None,
        remaining_minutes: int | None = None,
    ) -> TurnState:
        if self._closed or self._gateway is None:
            raise SessionClosedError("SessionRuntime has been closed")

        if self._graph is None:
            self._graph = build_turn_graph(self._gateway)

        state = TurnState(
            turn_index=turn_index,
            question=question,
            answer=answer,
            framework_json=framework_json,
            recent_turns=recent_turns or [],
            previous_summary=previous_summary,
            remaining_minutes=remaining_minutes,
        )

        # Wrap the per-turn work in a TaskGroup so a failure inside the
        # graph propagates cleanly without orphaning parallel work.
        async with asyncio.TaskGroup() as tg:
            self._task_group = tg
            graph_task = tg.create_task(self._graph.ainvoke(state))
        self._task_group = None

        final_dict = graph_task.result()
        final_state = TurnState.model_validate(final_dict)

        await self._emit_turn_events(final_state)

        # Reference answer is fire-and-forget — don't block the turn loop on it.
        ref_task = asyncio.create_task(
            self._run_reference_answer(turn_index, question, answer)
        )
        self._ref_answer_tasks.add(ref_task)
        ref_task.add_done_callback(self._ref_answer_tasks.discard)

        return final_state

    async def _run_reference_answer(self, turn_index: int, question: str, answer: str) -> None:
        if self._gateway is None:
            return
        try:
            result = await ReferenceAgentService().run(
                ReferenceAgentInput(question=question, candidate_answer=answer),
                self._gateway,
            )
        except Exception:
            # Reference is advisory; swallow rather than surface as a turn error.
            # WS layer can emit a typed error from its own monitor loop if desired.
            return
        await self._event_queue.put(
            ReferenceAnswerReadyEvent(
                turn_index=turn_index,
                answer_outline=tuple(result.answer_outline),
                ideal_answer=result.ideal_answer,
                key_evaluation_points=tuple(result.key_evaluation_points),
                common_pitfalls=tuple(result.common_pitfalls),
            )
        )

    async def _emit_turn_events(self, state: TurnState) -> None:
        if state.assessment is not None:
            await self._event_queue.put(
                TurnAssessedEvent(
                    turn_index=state.turn_index,
                    summary=state.assessment.summary,
                    strengths=tuple(state.assessment.strengths),
                    weaknesses=tuple(state.assessment.weaknesses),
                )
            )
        if state.compressed is not None:
            await self._event_queue.put(
                TurnCompressedEvent(
                    summary=state.compressed.summary,
                    preserved_keywords=tuple(state.compressed.preserved_keywords),
                    open_threads=tuple(state.compressed.open_threads),
                )
            )
        if state.next_question is not None:
            nq = state.next_question
            await self._event_queue.put(
                QuestionGeneratedEvent(
                    turn_index=state.turn_index + 1,
                    question=nq.question,
                    intent=nq.intent,
                    expected_depth=nq.expected_depth,
                    followup_hint=nq.followup_hint,
                    should_end=nq.should_end,
                )
            )

    async def on_session_end(self) -> None:
        if self._closed:
            return
        self._closed = True

        for task in list(self._ref_answer_tasks):
            task.cancel()
        for task in list(self._ref_answer_tasks):
            try:
                await task
            except (asyncio.CancelledError, Exception):
                pass
        self._ref_answer_tasks.clear()

        while not self._event_queue.empty():
            try:
                self._event_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

        # Drop every reference that transitively pins the LLMConfig so
        # gc.collect() can reclaim it. Order matters: graph closes over
        # gateway, gateway holds config — release the downstream refs
        # before nil-ing `_llm_config` itself.
        self._graph = None
        self._gateway = None
        self._task_group = None
        self._llm_config = None
