from __future__ import annotations

from app.agents.framework.schemas import FrameworkAgentInput, FrameworkAgentOutput
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class FrameworkAgentService:
    async def run(
        self, input: FrameworkAgentInput, gateway: LLMGateway
    ) -> FrameworkAgentOutput:
        system = render_prompt("framework", "system")
        user = render_prompt(
            "framework",
            "user",
            parse_payload_json=input.parse_payload_json,
            config=input.config.model_dump(),
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=FrameworkAgentOutput,
        )
