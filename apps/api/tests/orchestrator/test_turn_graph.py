from __future__ import annotations

import json
from typing import Any

import pytest

from app.infra.llm.gateway import LLMGateway
from app.orchestrator.state import TurnState
from app.orchestrator.turn_graph import build_turn_graph
from tests.agents._fakes import make_response

_ASSESSMENT_PAYLOAD = {
    "summary": "回答清晰但缺量化",
    "strengths": ["结构清楚"],
    "weaknesses": ["未给指标"],
}

_COMPRESSION_PAYLOAD = {
    "summary": "候选人围绕北极星指标给出选择逻辑,量化略薄。",
    "preserved_keywords": ["北极星指标", "A/B"],
    "open_threads": ["counter metric 还没问"],
}

_INTERVIEWER_PAYLOAD = {
    "question": "这个指标上线后有没有意外?",
    "intent": "验证是否跟过线上数据",
    "expected_depth": "tactical",
    "followup_hint": None,
    "should_end": False,
}


class RoutingGateway(LLMGateway):
    """Routes each call to the canned JSON whose keys match the system prompt.

    The three nodes issue completions in parallel; we can't rely on call
    ordering. Instead we sniff the system message and dispatch to the
    right payload. That keeps the test robust against LangGraph's
    scheduler re-ordering fan-out.
    """

    def __init__(self) -> None:
        self.calls_by_kind: dict[str, int] = {
            "turn_assessment": 0,
            "compression": 0,
            "interviewer": 0,
        }

    async def complete(self, messages: list[dict[str, Any]], **_kwargs: Any) -> Any:
        system = messages[0]["content"] if messages else ""
        if "面试复盘助理" in system:
            self.calls_by_kind["turn_assessment"] += 1
            return make_response(json.dumps(_ASSESSMENT_PAYLOAD))
        if "CompressionAgent" in system:
            self.calls_by_kind["compression"] += 1
            return make_response(json.dumps(_COMPRESSION_PAYLOAD))
        if "InterviewerAgent" in system:
            self.calls_by_kind["interviewer"] += 1
            return make_response(json.dumps(_INTERVIEWER_PAYLOAD))
        raise AssertionError(f"unroutable system prompt: {system[:80]!r}")


@pytest.fixture
def gateway() -> RoutingGateway:
    return RoutingGateway()


async def test_turn_graph_runs_three_nodes_and_merges_state(gateway: RoutingGateway) -> None:
    graph = build_turn_graph(gateway)

    initial = TurnState(
        turn_index=1,
        question="你怎么选北极星指标?",
        answer="我们当时选了完成率。",
        framework_json=json.dumps({"direction": "project_deep_dive"}),
        recent_turns=[],
        previous_summary=None,
        remaining_minutes=20,
    )

    result = await graph.ainvoke(initial)
    final = TurnState.model_validate(result)

    assert final.assessment is not None
    assert final.assessment.summary == _ASSESSMENT_PAYLOAD["summary"]

    assert final.compressed is not None
    assert final.compressed.summary == _COMPRESSION_PAYLOAD["summary"]

    assert final.next_question is not None
    assert final.next_question.question == _INTERVIEWER_PAYLOAD["question"]

    assert gateway.calls_by_kind == {
        "turn_assessment": 1,
        "compression": 1,
        "interviewer": 1,
    }
