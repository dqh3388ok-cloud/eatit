from __future__ import annotations

import asyncio
import json
from typing import Any
from unittest.mock import patch

import pytest

from app.agents.compression.schemas import (
    CompressionAgentInput,
    CompressionAgentOutput,
    CompressionTurn,
)
from app.agents.compression.service import CompressionAgentService
from tests.agents._fakes import ScriptedGateway, make_response

_GOOD_PAYLOAD = {
    "summary": "候选人围绕两个 LLM 产品项目展开,指标环节清晰,复盘量化不足。",
    "preserved_keywords": ["文档摘要 agent", "北极星指标", "A/B 框架"],
    "open_threads": ["失败项目的真实原因未确认"],
}


@pytest.fixture
def agent_input() -> CompressionAgentInput:
    return CompressionAgentInput(
        previous_summary=None,
        turns=[
            CompressionTurn(question="Q1", answer="A1"),
            CompressionTurn(question="Q2", answer="A2"),
            CompressionTurn(question="Q3", answer="A3"),
        ],
    )


async def test_compression_happy_path(agent_input: CompressionAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await CompressionAgentService().run(agent_input, gateway)

    assert isinstance(result, CompressionAgentOutput)
    assert len(result.preserved_keywords) == 3
    assert gateway.calls == 1


async def test_compression_retries_on_malformed_json(
    agent_input: CompressionAgentInput,
) -> None:
    gateway = ScriptedGateway(["garbage", json.dumps(_GOOD_PAYLOAD)])

    result = await CompressionAgentService().run(agent_input, gateway)

    assert isinstance(result, CompressionAgentOutput)
    assert gateway.calls == 2


async def test_compression_times_out_to_degraded_summary(
    agent_input: CompressionAgentInput,
) -> None:
    """If the LLM call exceeds the 3s budget, return a degraded, LLM-free summary
    built from the last two turns so the orchestrator keeps moving."""

    class SlowGateway:
        calls = 0

        async def complete(self, messages: list[dict[str, Any]], **_kwargs: Any) -> Any:
            SlowGateway.calls += 1
            await asyncio.sleep(0.5)  # deliberately slower than the patched timeout
            return make_response(json.dumps(_GOOD_PAYLOAD))

    # Patch the timeout down so the test stays fast. This also verifies the
    # wait_for wrapper is reached (a bug that bypassed wait_for would sleep
    # through the patched budget and fail).
    with patch(
        "app.agents.compression.service.COMPRESSION_TIMEOUT_SECONDS",
        0.01,
    ):
        result = await CompressionAgentService().run(agent_input, SlowGateway())

    assert isinstance(result, CompressionAgentOutput)
    assert result.preserved_keywords == []
    assert result.open_threads == []
    assert "降级" in result.summary or "未生成" in result.summary
