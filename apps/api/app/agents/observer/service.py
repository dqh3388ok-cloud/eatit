from __future__ import annotations

from app.agents.observer.schemas import ObserverAgentInput, ObserverAgentOutput
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class ObserverAgentService:
    async def run(
        self, input: ObserverAgentInput, gateway: LLMGateway
    ) -> ObserverAgentOutput:
        system = render_prompt("observer", "system")
        user = render_prompt(
            "observer",
            "user",
            turn_index=input.turn_index,
            question=input.question,
            answer=input.answer,
            remaining_minutes=input.remaining_minutes,
            long_term_summary=input.long_term_summary,
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=ObserverAgentOutput,
        )
