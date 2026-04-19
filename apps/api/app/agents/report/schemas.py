from pydantic import BaseModel, Field


class ReportAgentOutput(BaseModel):
    overall_summary: str = Field(default="", description="Placeholder report summary")
