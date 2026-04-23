from __future__ import annotations

import asyncio

from pydantic import SecretStr

from app.agents.observer.schemas import ObserverAgentOutput
from app.agents.observer.service import ObserverAgentService
from app.infra.llm.config import LLMConfig
from app.orchestrator.events import ObserverObservationEvent
from app.orchestrator.runtime import SessionRuntime
from app.orchestrator.state import TurnState


def _config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        api_key=SecretStr("sk-observer-test"),
        model="gpt-4o-mini",
        base_url=None,
    )


class _StubGraph:
    """Minimal graph double that skips all agents and returns a valid final state."""

    async def ainvoke(self, state: TurnState) -> dict:
        return state.model_dump(mode="python")


def _install_stub_graph(runtime: SessionRuntime) -> None:
    # Pre-populate `_graph` so `run_turn` skips the real build_turn_graph call.
    runtime._graph = _StubGraph()


async def _wait_for_tasks(runtime: SessionRuntime, timeout: float = 2.0) -> None:
    deadline = asyncio.get_event_loop().time() + timeout
    while runtime._observer_tasks or runtime._ref_answer_tasks:
        if asyncio.get_event_loop().time() > deadline:
            raise AssertionError("observer/reference tasks did not complete in time")
        await asyncio.sleep(0.01)


async def test_observer_event_enqueued_on_happy_path(monkeypatch) -> None:
    captured: dict = {}

    async def fake_observer_run(_self, input, _gateway):
        captured["turn_index"] = input.turn_index
        captured["question"] = input.question
        captured["answer"] = input.answer
        captured["remaining_minutes"] = input.remaining_minutes
        captured["long_term_summary"] = input.long_term_summary
        return ObserverAgentOutput(
            observation="你这段量化很到位,保持节奏",
            tone="support",
            actionable=False,
        )

    # Keep the reference task off the critical path for this test.
    from app.agents.reference.service import ReferenceAgentService

    async def _no_op_reference(_self, _input, _gateway):
        raise RuntimeError("reference not exercised in this test")

    monkeypatch.setattr(ObserverAgentService, "run", fake_observer_run)
    monkeypatch.setattr(ReferenceAgentService, "run", _no_op_reference)

    runtime = SessionRuntime(session_id="sess-observer-ok", llm_config=_config())
    _install_stub_graph(runtime)

    try:
        await runtime.run_turn(
            turn_index=2,
            question="你怎么衡量这个功能上线是否成功?",
            answer="我们先锁完成率,再看留存。完成率从 42% 提到 58%。",
            framework_json="{}",
            previous_summary="历史摘要占位",
            remaining_minutes=7,
        )
        await _wait_for_tasks(runtime)

        # Pull every event the runtime emitted; the observer event must be
        # present with a shape matching ObserverObservationEvent.
        drained: list = []
        while not runtime.event_queue.empty():
            drained.append(runtime.event_queue.get_nowait())
    finally:
        await runtime.on_session_end()

    observer_events = [e for e in drained if isinstance(e, ObserverObservationEvent)]
    assert len(observer_events) == 1
    evt = observer_events[0]
    assert evt.turn_index == 2
    assert evt.tone == "support"
    assert evt.actionable is False
    assert evt.observation == "你这段量化很到位,保持节奏"

    # Agent input was threaded through run_turn -> _run_observer correctly.
    assert captured["turn_index"] == 2
    assert captured["remaining_minutes"] == 7
    assert captured["long_term_summary"] == "历史摘要占位"


async def test_observer_failure_does_not_break_turn(monkeypatch) -> None:
    async def boom(_self, _input, _gateway):
        raise RuntimeError("observer upstream down")

    # Reference agent also stubbed so nothing real fires.
    from app.agents.reference.service import ReferenceAgentService

    async def _no_op_reference(_self, _input, _gateway):
        raise RuntimeError("reference not exercised in this test")

    monkeypatch.setattr(ObserverAgentService, "run", boom)
    monkeypatch.setattr(ReferenceAgentService, "run", _no_op_reference)

    runtime = SessionRuntime(session_id="sess-observer-boom", llm_config=_config())
    _install_stub_graph(runtime)

    try:
        # The turn must complete without re-raising the observer error.
        await runtime.run_turn(
            turn_index=3,
            question="说一个你主导的项目",
            answer="我做过一个文档摘要 agent",
            framework_json="{}",
        )
        await _wait_for_tasks(runtime)

        drained: list = []
        while not runtime.event_queue.empty():
            drained.append(runtime.event_queue.get_nowait())
    finally:
        await runtime.on_session_end()

    assert not any(isinstance(e, ObserverObservationEvent) for e in drained)


async def test_duplicate_turn_end_only_schedules_one_observer(monkeypatch) -> None:
    call_count = 0

    async def counting_run(_self, _input, _gateway):
        nonlocal call_count
        call_count += 1
        return ObserverAgentOutput(
            observation="保持", tone="support", actionable=False
        )

    from app.agents.reference.service import ReferenceAgentService

    async def _no_op_reference(_self, _input, _gateway):
        raise RuntimeError("reference not exercised in this test")

    monkeypatch.setattr(ObserverAgentService, "run", counting_run)
    monkeypatch.setattr(ReferenceAgentService, "run", _no_op_reference)

    runtime = SessionRuntime(session_id="sess-observer-dup", llm_config=_config())
    _install_stub_graph(runtime)

    try:
        await runtime.run_turn(
            turn_index=4, question="Q", answer="A", framework_json="{}"
        )
        # Simulate a buggy client resending the same turn_index.
        await runtime.run_turn(
            turn_index=4, question="Q", answer="A", framework_json="{}"
        )
        await _wait_for_tasks(runtime)
    finally:
        await runtime.on_session_end()

    assert call_count == 1
