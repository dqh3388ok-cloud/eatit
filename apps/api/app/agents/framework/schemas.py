from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class FrameworkConfigInput(BaseModel):
    level: str
    style: str
    duration_minutes: int = Field(ge=1)


class FrameworkAgentInput(BaseModel):
    parse_payload_json: str
    config: FrameworkConfigInput


class FocusCompetency(BaseModel):
    title: str
    why: str
    probe_hint: str


class DeepDiveAnchor(BaseModel):
    anchor: str
    probe_chain: list[str]


class PaceSegment(BaseModel):
    name: str
    rough_minutes: int = Field(ge=1)
    goal: str


class PacePlan(BaseModel):
    total_minutes: int = Field(ge=1)
    segments: list[PaceSegment]


class FrameworkAgentOutput(BaseModel):
    direction: Literal["project_deep_dive", "competency_probe", "culture_fit", "hybrid"]
    focus_competencies: list[FocusCompetency]
    opening_questions: list[str]
    deep_dive_anchors: list[DeepDiveAnchor]
    pace_plan: PacePlan
