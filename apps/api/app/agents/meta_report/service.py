from __future__ import annotations

import json

from app.agents.meta_report.schemas import MetaReportAgentInput, MetaReportOutput
from app.infra.llm import LLMGateway
from app.infra.llm.instructor_client import make_instructor, structured_completion
from app.prompts import render_prompt


class MetaReportAgentService:
    async def run(self, input: MetaReportAgentInput, gateway: LLMGateway) -> MetaReportOutput:
        sessions_json = json.dumps(
            [s.model_dump(mode="json") for s in input.sessions],
            ensure_ascii=False,
        )
        system = render_prompt(
            "meta_report",
            "system",
            session_count=len(input.sessions),
        )
        user = render_prompt(
            "meta_report",
            "user",
            session_count=len(input.sessions),
            sessions_json=sessions_json,
        )
        client = make_instructor(gateway)
        return await structured_completion(
            client,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            response_model=MetaReportOutput,
        )
