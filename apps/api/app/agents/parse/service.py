from __future__ import annotations

from app.agents.parse.schemas import ParseAgentInput, ParseAgentOutput
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class ParseAgentService:
    async def run(self, input: ParseAgentInput, gateway: LLMGateway) -> ParseAgentOutput:
        system = render_prompt("parse", "system")
        user = render_prompt(
            "parse",
            "user",
            resume_text=input.resume_text,
            jd_text=input.jd_text,
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=ParseAgentOutput,
        )
