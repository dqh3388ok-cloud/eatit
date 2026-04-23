from __future__ import annotations

import json

import pytest

from app.agents.observer.schemas import ObserverAgentInput, ObserverAgentOutput
from app.agents.observer.service import ObserverAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway


_GOOD_PAYLOAD = {
    "observation": "你这段量化很到位,保持节奏",
    "tone": "support",
    "actionable": False,
}


@pytest.fixture
def agent_input() -> ObserverAgentInput:
    return ObserverAgentInput(
        turn_index=2,
        question="你怎么衡量这个功能上线是否成功?",
        answer="我会先锁定完成率,再看留存。上线一周后我们把完成率从 42% 提到 58%。",
        remaining_minutes=8,
        long_term_summary=None,
    )


async def test_observer_happy_path(agent_input: ObserverAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await ObserverAgentService().run(agent_input, gateway)

    assert isinstance(result, ObserverAgentOutput)
    assert result.tone == "support"
    assert len(result.observation) <= 60
    assert result.actionable is False
    assert gateway.calls == 1


async def test_observer_retries_and_enforces_60_char_cap(
    agent_input: ObserverAgentInput,
) -> None:
    over_limit = {
        "observation": "你这段表现还挺稳的" * 20,  # far past the 60-char cap
        "tone": "support",
        "actionable": False,
    }
    recovered = {
        "observation": "你偏题了,拉回问题本身",
        "tone": "alert",
        "actionable": True,
    }
    gateway = ScriptedGateway([json.dumps(over_limit), json.dumps(recovered)])

    result = await ObserverAgentService().run(agent_input, gateway)

    # Instructor rejects the first payload on schema validation (max_length=60)
    # and asks the gateway again; the second reply validates cleanly.
    assert result.tone == "alert"
    assert len(result.observation) <= 60
    assert gateway.calls == 2


async def test_observer_propagates_network_error(
    agent_input: ObserverAgentInput,
) -> None:
    gateway = ScriptedGateway([LLMNetworkError("offline")] * 3)

    with pytest.raises(LLMNetworkError):
        await ObserverAgentService().run(agent_input, gateway)
