from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

ObserverTone = Literal["support", "alert", "pivot"]


class ObserverAgentInput(BaseModel):
    turn_index: int = Field(ge=0)
    question: str
    answer: str
    remaining_minutes: int | None = None
    long_term_summary: str | None = None


class ObserverAgentOutput(BaseModel):
    observation: str = Field(min_length=1, max_length=60)
    tone: ObserverTone
    actionable: bool
