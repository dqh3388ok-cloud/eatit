from pydantic import BaseModel, Field


class InterviewerAgentOutput(BaseModel):
    question_text: str = Field(default="", description="Placeholder interviewer question")
