from __future__ import annotations

from pydantic import Field

from app.models.enums import InterviewDirection, InterviewStyle
from app.schemas.common import SchemaModel


class FrameworkStage(SchemaModel):
    name: str
    goal: str
    question_budget: int = Field(ge=1)


class DirectionFramework(SchemaModel):
    style: InterviewStyle
    direction: InterviewDirection
    duration_minutes: int = Field(ge=1)
    stages: list[FrameworkStage]
    focus_points: list[str]
    risk_points: list[str]
