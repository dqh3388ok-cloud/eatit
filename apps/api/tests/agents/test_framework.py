from __future__ import annotations

import json

import pytest

from app.agents.framework.schemas import (
    FrameworkAgentInput,
    FrameworkAgentOutput,
    FrameworkConfigInput,
)
from app.agents.framework.service import FrameworkAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway

_GOOD_PAYLOAD = {
    "direction": "project_deep_dive",
    "focus_competencies": [
        {"title": "需求抽象", "why": "AI PM 核心能力", "probe_hint": "从 0→1 项目切入"}
    ],
    "opening_questions": ["请先简单介绍你最近一个完整上线的项目"],
    "deep_dive_anchors": [
        {
            "anchor": "AI 面试官",
            "probe_chain": ["what", "why", "how", "what-if"],
        }
    ],
    "pace_plan": {
        "total_minutes": 30,
        "segments": [
            {"name": "暖场", "rough_minutes": 3, "goal": "破冰"},
            {"name": "项目深挖", "rough_minutes": 18, "goal": "核心能力"},
            {"name": "能力追问", "rough_minutes": 7, "goal": "补全维度"},
            {"name": "反问", "rough_minutes": 2, "goal": "候选人提问"},
        ],
    },
}


@pytest.fixture
def agent_input() -> FrameworkAgentInput:
    return FrameworkAgentInput(
        parse_payload_json=json.dumps({"match_summary": "mock"}),
        config=FrameworkConfigInput(level="senior", style="deep", duration_minutes=30),
    )


async def test_framework_happy_path(agent_input: FrameworkAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await FrameworkAgentService().run(agent_input, gateway)

    assert isinstance(result, FrameworkAgentOutput)
    assert result.direction == "project_deep_dive"
    assert result.pace_plan.total_minutes == 30
    assert gateway.calls == 1


async def test_framework_retries_on_malformed_json(agent_input: FrameworkAgentInput) -> None:
    gateway = ScriptedGateway(["not json at all", json.dumps(_GOOD_PAYLOAD)])

    result = await FrameworkAgentService().run(agent_input, gateway)

    assert isinstance(result, FrameworkAgentOutput)
    assert gateway.calls == 2


async def test_framework_propagates_network_error(agent_input: FrameworkAgentInput) -> None:
    gateway = ScriptedGateway([LLMNetworkError("boom")] * 3)

    with pytest.raises(LLMNetworkError):
        await FrameworkAgentService().run(agent_input, gateway)
