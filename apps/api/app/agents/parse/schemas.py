from pydantic import BaseModel, Field


class ParseAgentOutput(BaseModel):
    match_summary: str = Field(default="", description="Placeholder parse result")
