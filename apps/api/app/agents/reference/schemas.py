from pydantic import BaseModel, Field


class ReferenceAgentOutput(BaseModel):
    answer_script: str = Field(default="", description="Placeholder reference answer")
