from pydantic import BaseModel, Field


class FrameworkAgentOutput(BaseModel):
    framework_summary: str = Field(default="", description="Placeholder framework result")
