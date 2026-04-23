"""Per-turn state for the LangGraph `turn_graph`.

Pydantic BaseModel (not `@dataclass`) so Instructor can read fields via
`.model_dump()` and so LangGraph's state merging honours `Annotated`
reducer hints if we ever need them (e.g. for accumulated events).

Shape of a single invocation:
  inputs  — set before `graph.ainvoke(...)` by the runtime
  outputs — populated by each node; start as None so a failed node leaves
            a clear "did not run" signal rather than a silent default.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.agents.compression.schemas import CompressionAgentOutput
from app.agents.interviewer.schemas import InterviewerAgentOutput, TurnRecord


class TurnAssessment(BaseModel):
    summary: str
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)


class TurnState(BaseModel):
    turn_index: int = Field(ge=0)
    question: str
    answer: str
    framework_json: str
    recent_turns: list[TurnRecord] = Field(default_factory=list)
    previous_summary: str | None = None
    remaining_minutes: int | None = None

    assessment: TurnAssessment | None = None
    compressed: CompressionAgentOutput | None = None
    next_question: InterviewerAgentOutput | None = None
