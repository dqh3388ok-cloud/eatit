from __future__ import annotations

from app.agents.reference.schemas import ReferenceAgentInput, ReferenceAgentOutput
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class ReferenceAgentService:
    async def run(
        self, input: ReferenceAgentInput, gateway: LLMGateway
    ) -> ReferenceAgentOutput:
        system = render_prompt("reference", "system")
        user = render_prompt(
            "reference",
            "user",
            question=input.question,
            job_context=input.job_context,
            candidate_answer=input.candidate_answer,
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=ReferenceAgentOutput,
        )
