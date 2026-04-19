from pydantic import BaseModel, Field


class CompressionAgentOutput(BaseModel):
    summary: str = Field(default="", description="Placeholder compressed turn summary")
