from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import pytest

from app.infra.llm.gateway import LLMGateway
from app.orchestrator.state import TurnState
from app.orchestrator.turn_graph import build_turn_graph
from tests.agents._fakes import make_response

_ASSESSMENT_PAYLOAD = {
    "summary": "候选人答得中规中矩",
    "strengths": [],
    "weaknesses": [],
}

_INTERVIEWER_PAYLOAD = {
    "question": "展开说说指标的上线过程",
    "intent": "深挖落地",
    "expected_depth": "tactical",
    "followup_hint": None,
    "should_end": False,
}


class SlowCompressionGateway(LLMGateway):
    """Fast for assessment + interviewer, intentionally slow for compression."""

    async def complete(self, messages: list[dict[str, Any]], **_kwargs: Any) -> Any:
        system = messages[0]["content"] if messages else ""
        if "CompressionAgent" in system:
            # Longer than the patched timeout budget so wait_for fires.
            await asyncio.sleep(0.2)
            return make_response("{}")
        if "面试复盘助理" in system:
            return make_response(json.dumps(_ASSESSMENT_PAYLOAD))
        if "InterviewerAgent" in system:
            return make_response(json.dumps(_INTERVIEWER_PAYLOAD))
        raise AssertionError(f"unexpected system prompt: {system[:80]!r}")


@pytest.fixture
def gateway() -> SlowCompressionGateway:
    return SlowCompressionGateway()


async def test_graph_uses_degraded_summary_when_compression_times_out(
    gateway: SlowCompressionGateway,
) -> None:
    # Patch the compression budget down to something well under the fake
    # gateway's 0.2s sleep so the degraded path is deterministic.
    with patch(
        "app.agents.compression.service.COMPRESSION_TIMEOUT_SECONDS",
        0.02,
    ):
        graph = build_turn_graph(gateway)

        initial = TurnState(
            turn_index=2,
            question="北极星指标选完后怎么上线?",
            answer="我们用 A/B 验证后灰度。",
            framework_json=json.dumps({"direction": "project_deep_dive"}),
            recent_turns=[],
            previous_summary=None,
            remaining_minutes=15,
        )

        result = await graph.ainvoke(initial)

    final = TurnState.model_validate(result)

    assert final.compressed is not None
    # Degraded summary is LLM-free and leaves keyword/thread lists empty.
    assert final.compressed.preserved_keywords == []
    assert final.compressed.open_threads == []
    assert "降级" in final.compressed.summary

    # The other nodes still ran despite compression falling back.
    assert final.assessment is not None
    assert final.next_question is not None
