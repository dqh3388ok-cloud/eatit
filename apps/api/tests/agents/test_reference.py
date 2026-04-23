from __future__ import annotations

import json

import pytest

from app.agents.reference.schemas import ReferenceAgentInput, ReferenceAgentOutput
from app.agents.reference.service import ReferenceAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway

_GOOD_PAYLOAD = {
    "answer_outline": [
        "先锁用户价值",
        "再拆可被影响的中间量",
        "确保指标有反脆弱性",
    ],
    "ideal_answer": "以文档摘要 agent 为例,北极星指标应该锁在...",
    "key_evaluation_points": ["是否归因到模型改动", "是否能迭代"],
    "common_pitfalls": ["一上来就用 DAU", "指标无法归因"],
}


@pytest.fixture
def agent_input() -> ReferenceAgentInput:
    return ReferenceAgentInput(
        question="在 0 到 1 的 LLM 产品里,你怎么选北极星指标?",
        job_context="AI PM",
        candidate_answer=None,
    )


async def test_reference_happy_path(agent_input: ReferenceAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await ReferenceAgentService().run(agent_input, gateway)

    assert isinstance(result, ReferenceAgentOutput)
    assert len(result.answer_outline) == 3
    assert gateway.calls == 1


async def test_reference_retries_on_malformed_json(
    agent_input: ReferenceAgentInput,
) -> None:
    gateway = ScriptedGateway(["no json", json.dumps(_GOOD_PAYLOAD)])

    result = await ReferenceAgentService().run(agent_input, gateway)

    assert isinstance(result, ReferenceAgentOutput)
    assert gateway.calls == 2


async def test_reference_propagates_network_error(
    agent_input: ReferenceAgentInput,
) -> None:
    gateway = ScriptedGateway([LLMNetworkError("network down")] * 3)

    with pytest.raises(LLMNetworkError):
        await ReferenceAgentService().run(agent_input, gateway)
