from __future__ import annotations

import json

import pytest

from app.agents.parse.schemas import ParseAgentInput, ParseAgentOutput
from app.agents.parse.service import ParseAgentService
from app.infra.llm.errors import LLMNetworkError
from tests.agents._fakes import ScriptedGateway

_GOOD_PAYLOAD = {
    "job_requirements": [{"title": "岗位理解", "detail": "把项目经历映射到目标岗位"}],
    "candidate_highlights": [{"title": "结果导向", "detail": "会说明项目结果"}],
    "candidate_risks": [{"title": "数据不足", "detail": "需补充业务指标"}],
    "project_hooks": [
        {
            "project_name": "AI 面试官",
            "reason": "与目标岗位相关",
            "focus_points": ["场景选择", "指标设计"],
        }
    ],
    "match_summary": "候选人整体匹配但量化欠缺",
}


@pytest.fixture
def agent_input() -> ParseAgentInput:
    return ParseAgentInput(resume_text="候选人简历", jd_text="岗位描述")


async def test_parse_happy_path_returns_structured_output(agent_input: ParseAgentInput) -> None:
    gateway = ScriptedGateway([json.dumps(_GOOD_PAYLOAD)])

    result = await ParseAgentService().run(agent_input, gateway)

    assert isinstance(result, ParseAgentOutput)
    assert result.match_summary == "候选人整体匹配但量化欠缺"
    assert len(result.project_hooks) == 1
    assert gateway.calls == 1


async def test_parse_retries_on_malformed_json(agent_input: ParseAgentInput) -> None:
    gateway = ScriptedGateway(["这不是 JSON", json.dumps(_GOOD_PAYLOAD)])

    result = await ParseAgentService().run(agent_input, gateway)

    assert isinstance(result, ParseAgentOutput)
    assert gateway.calls == 2


async def test_parse_propagates_llm_network_error(agent_input: ParseAgentInput) -> None:
    # Instructor retries up to `max_retries` times on any failure, so we have
    # to queue the same error for every attempt; our wrapper unwraps the
    # InstructorRetryException and re-raises the original typed error.
    gateway = ScriptedGateway([LLMNetworkError("upstream offline")] * 3)

    with pytest.raises(LLMNetworkError):
        await ParseAgentService().run(agent_input, gateway)
