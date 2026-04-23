from __future__ import annotations

from app.agents.interviewer.schemas import (
    InterviewerAgentInput,
    InterviewerAgentOutput,
)
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class InterviewerAgentService:
    async def run(
        self, input: InterviewerAgentInput, gateway: LLMGateway
    ) -> InterviewerAgentOutput:
        system = render_prompt("interviewer", "system")
        user = render_prompt(
            "interviewer",
            "user",
            framework_json=input.framework_json,
            recent_turns=[t.model_dump() for t in input.recent_turns],
            long_term_summary=input.long_term_summary,
            remaining_minutes=input.remaining_minutes,
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=InterviewerAgentOutput,
        )
