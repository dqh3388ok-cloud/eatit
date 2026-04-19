from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.schemas.common import SchemaModel, TimestampedResponse


class JobRequirement(SchemaModel):
    title: str
    detail: str


class CandidateHighlight(SchemaModel):
    title: str
    detail: str


class CandidateRisk(SchemaModel):
    title: str
    detail: str


class ProjectHook(SchemaModel):
    project_name: str
    reason: str
    focus_points: list[str]


class ParseResultPayload(SchemaModel):
    job_requirements: list[JobRequirement]
    candidate_highlights: list[CandidateHighlight]
    candidate_risks: list[CandidateRisk]
    project_hooks: list[ProjectHook]
    match_summary: str


class ParseRequestResponse(SchemaModel):
    asset_bundle_id: UUID
    status: str
    payload: ParseResultPayload


class ParseResultResponse(TimestampedResponse):
    candidate_asset_id: UUID
    status: str
    payload: ParseResultPayload


class ParseResultPreview(SchemaModel):
    match_summary: str
    candidate_risk_count: int = Field(ge=0)
    project_hook_count: int = Field(ge=0)
