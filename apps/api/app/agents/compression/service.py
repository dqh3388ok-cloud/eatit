from __future__ import annotations

import asyncio

from app.agents.compression.schemas import (
    CompressionAgentInput,
    CompressionAgentOutput,
)
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt

COMPRESSION_TIMEOUT_SECONDS: float = 3.0


def _degraded_summary(input: CompressionAgentInput) -> CompressionAgentOutput:
    """Build a deterministic, no-LLM summary from the last two turns.

    Used when the LLM call exceeds `COMPRESSION_TIMEOUT_SECONDS`. Keeps the
    orchestrator unblocked instead of stalling the whole turn loop on a slow
    upstream. preserved_keywords / open_threads are intentionally left empty so
    downstream consumers can tell a degraded payload from a real one.
    """
    tail = input.turns[-2:]
    if not tail:
        text = "（本次压缩未生成:无对话可压缩）"
    else:
        lines = [f"Q{i}: {t.question} / A{i}: {t.answer}" for i, t in enumerate(tail)]
        text = "压缩超时,降级保留最近两轮原文:\n" + "\n".join(lines)
    return CompressionAgentOutput(summary=text, preserved_keywords=[], open_threads=[])


class CompressionAgentService:
    async def run(
        self, input: CompressionAgentInput, gateway: LLMGateway
    ) -> CompressionAgentOutput:
        system = render_prompt("compression", "system")
        user = render_prompt(
            "compression",
            "user",
            previous_summary=input.previous_summary,
            turns=[t.model_dump() for t in input.turns],
        )
        client = make_instructor(gateway)

        try:
            return await asyncio.wait_for(
                structured_completion(
                    client,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_model=CompressionAgentOutput,
                ),
                timeout=COMPRESSION_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return _degraded_summary(input)
