from __future__ import annotations

from pydantic import BaseModel

from app.schemas.parse import ParseResultPayload


class ParseAgentInput(BaseModel):
    resume_text: str
    jd_text: str


class ParseAgentOutput(ParseResultPayload):
    pass
