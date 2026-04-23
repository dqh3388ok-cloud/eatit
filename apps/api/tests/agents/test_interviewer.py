from __future__ import annotations

import json

import pytest

from app.agents.interviewer.schemas import (
    InterviewerAgentInput,
    InterviewerAgentOutput,
    TurnRecord,
)
from app.agents.interviewer.service import InterviewerAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway

_GOOD_PAYLOAD = {
    "question": "这个指标上线后有没有跟你预期不一致的地方?",
    "intent": "验证候选人是否真的跟过线上数据",
    "expected_depth": "tactical",
    "followup_hint": "继续追问 counter metric",
    "should_end": False,
}


@pytest.fixture
def agent_input() -> InterviewerAgentInput:
    return InterviewerAgentInput(
        framework_json=json.dumps({"direction": "project_deep_dive"}),
        recent_turns=[TurnRecord(question="上一题", answer="上一答")],
        long_term_summary=None,
        remaining_minutes=20,
    )


async def test_interviewer_happy_path(agent_input: InterviewerAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await InterviewerAgentService().run(agent_input, gateway)

    assert isinstance(result, InterviewerAgentOutput)
    assert result.expected_depth == "tactical"
    assert result.should_end is False
    assert gateway.calls == 1


async def test_interviewer_retries_on_malformed_json(
    agent_input: InterviewerAgentInput,
) -> None:
    gateway = ScriptedGateway(["<<broken>>", json.dumps(_GOOD_PAYLOAD)])

    result = await InterviewerAgentService().run(agent_input, gateway)

    assert isinstance(result, InterviewerAgentOutput)
    assert gateway.calls == 2


async def test_interviewer_propagates_network_error(
    agent_input: InterviewerAgentInput,
) -> None:
    gateway = ScriptedGateway([LLMNetworkError("gone")] * 3)

    with pytest.raises(LLMNetworkError):
        await InterviewerAgentService().run(agent_input, gateway)
