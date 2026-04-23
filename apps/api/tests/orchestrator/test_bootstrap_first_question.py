from __future__ import annotations

import pytest
from pydantic import SecretStr

from app.agents.interviewer.schemas import InterviewerAgentOutput
from app.agents.interviewer.service import InterviewerAgentService
from app.infra.llm.config import LLMConfig
from app.orchestrator.events import QuestionGeneratedEvent
from app.orchestrator.runtime import SessionClosedError, SessionRuntime


def _config() -> LLMConfig:
    return LLMConfig(
        provider="openai",
        api_key=SecretStr("sk-bootstrap-test"),
        model="gpt-4o-mini",
        base_url=None,
    )


async def test_bootstrap_first_question_emits_turn_zero(monkeypatch) -> None:
    captured_input: dict = {}

    async def fake_run(_self, input, _gateway):
        captured_input["recent_turns"] = list(input.recent_turns)
        captured_input["framework_json"] = input.framework_json
        return InterviewerAgentOutput(
            question="介绍一下你最近主导的项目。",
            intent="暖场 + 打开项目深挖通道",
            expected_depth="surface",
            followup_hint="注意量化结果",
        )

    monkeypatch.setattr(InterviewerAgentService, "run", fake_run)

    runtime = SessionRuntime(session_id="session-bootstrap", llm_config=_config())
    try:
        await runtime.bootstrap_first_question(
            framework_json='{"direction":"project_deep_dive"}'
        )

        # Exactly one event queued, shape matches turn 0.
        event = runtime.event_queue.get_nowait()
        assert isinstance(event, QuestionGeneratedEvent)
        assert event.turn_index == 0
        assert event.question == "介绍一下你最近主导的项目。"
        assert event.expected_depth == "surface"
        assert event.followup_hint == "注意量化结果"
        assert runtime.event_queue.empty()

        # Agent saw an empty recent_turns (this is the bootstrap signal).
        assert captured_input["recent_turns"] == []
        assert "project_deep_dive" in captured_input["framework_json"]
    finally:
        await runtime.on_session_end()


async def test_bootstrap_rejects_after_close() -> None:
    runtime = SessionRuntime(session_id="session-closed", llm_config=_config())
    await runtime.on_session_end()

    with pytest.raises(SessionClosedError):
        await runtime.bootstrap_first_question(framework_json="{}")


async def test_bootstrap_propagates_agent_failure(monkeypatch) -> None:
    class _Boom(Exception):
        pass

    async def fake_run(_self, _input, _gateway):
        raise _Boom("upstream auth failed")

    monkeypatch.setattr(InterviewerAgentService, "run", fake_run)

    runtime = SessionRuntime(session_id="session-boom", llm_config=_config())
    try:
        with pytest.raises(_Boom):
            await runtime.bootstrap_first_question(framework_json="{}")
        # Failure must not leave a phantom event in the queue.
        assert runtime.event_queue.empty()
    finally:
        await runtime.on_session_end()
