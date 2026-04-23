from __future__ import annotations

import json

import pytest

from app.agents.report.schemas import (
    ReportAgentInput,
    ReportAgentOutput,
    ReportTurnRecord,
)
from app.agents.report.service import ReportAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway

_GOOD_PAYLOAD = {
    "pass_probability": 72,
    "summary": "候选人整体胜任,但若干维度需要复盘",
    "reasons": [
        {
            "aspect": "指标设计",
            "verdict": "solid",
            "evidence_turn_index": 1,
            "quote": "我们当时选了完成率作为北极星指标",
        },
        {
            "aspect": "失败复盘",
            "verdict": "weak",
            "evidence_turn_index": 3,
            "quote": "那次项目我主要是配合执行",
        },
    ],
    "next_actions": [
        "整理一份上线项目的指标体系表",
        "复盘最近两次失败项目的根因",
    ],
}


@pytest.fixture
def agent_input() -> ReportAgentInput:
    return ReportAgentInput(
        parse_payload_json=json.dumps({"match_summary": "mock"}),
        framework_json=json.dumps({"direction": "project_deep_dive"}),
        turns=[
            ReportTurnRecord(question="Q1", answer="A1"),
            ReportTurnRecord(question="Q2", answer="A2"),
        ],
        long_term_summary="候选人项目经验充分",
    )


async def test_report_happy_path(agent_input: ReportAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await ReportAgentService().run(agent_input, gateway)

    assert isinstance(result, ReportAgentOutput)
    assert 0 <= result.pass_probability <= 100
    assert result.reasons[0].verdict == "solid"
    assert len(result.next_actions) == 2
    assert gateway.calls == 1


async def test_report_retries_on_malformed_json(agent_input: ReportAgentInput) -> None:
    gateway = ScriptedGateway(["broken", json.dumps(_GOOD_PAYLOAD)])

    result = await ReportAgentService().run(agent_input, gateway)

    assert isinstance(result, ReportAgentOutput)
    assert gateway.calls == 2


async def test_report_propagates_network_error(agent_input: ReportAgentInput) -> None:
    gateway = ScriptedGateway([LLMNetworkError("offline")] * 3)

    with pytest.raises(LLMNetworkError):
        await ReportAgentService().run(agent_input, gateway)
