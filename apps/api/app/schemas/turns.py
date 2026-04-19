from __future__ import annotations

from pydantic import Field

from app.schemas.common import SchemaModel


class NormalizedQuestion(SchemaModel):
    turn_index: int = Field(ge=1)
    stage_name: str
    question_tag: str
    question_text: str


class NormalizedAnswer(SchemaModel):
    turn_index: int = Field(ge=1)
    transcript_text: str
    cleaned_sentences: list[str]
    key_points: list[str]


class NormalizedUserAssessment(SchemaModel):
    turn_index: int = Field(ge=1)
    strengths: list[str]
    weaknesses: list[str]
    risks: list[str]
    suggestions: list[str]
    evidence: list[str]
    score_optional: float | None = None


class CompressedTurnSummary(SchemaModel):
    turn_index: int = Field(ge=1)
    question_tag: str
    candidate_claims: list[str]
    metrics_mentioned: list[str]
    strengths: list[str]
    weaknesses: list[str]
    followup_candidates: list[str]
    toxicity_or_risk: list[str]


class ReferenceAnswer(SchemaModel):
    checkpoints: list[str]
    expected_project_familiarity: str
    expected_confidence: str
    answer_script: str
