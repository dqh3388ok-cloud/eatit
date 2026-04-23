from __future__ import annotations

from app.agents.report.schemas import ReportAgentInput, ReportAgentOutput
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class ReportAgentService:
    async def run(self, input: ReportAgentInput, gateway: LLMGateway) -> ReportAgentOutput:
        system = render_prompt("report", "system")
        user = render_prompt(
            "report",
            "user",
            parse_payload_json=input.parse_payload_json,
            framework_json=input.framework_json,
            turns=[t.model_dump() for t in input.turns],
            long_term_summary=input.long_term_summary,
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=ReportAgentOutput,
        )
