"""Protocol-agnostic orchestrator events.

The WebSocket layer (app/ws/schemas.py) owns the wire protocol. The
orchestrator emits these intermediate records and P3.5 maps them to
`Server*Event` payloads before serialization. Keeping the orchestrator
decoupled lets us unit-test turn logic without spinning up a WS.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class TurnAssessedEvent:
    turn_index: int
    summary: str
    strengths: tuple[str, ...]
    weaknesses: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class TurnCompressedEvent:
    summary: str
    preserved_keywords: tuple[str, ...]
    open_threads: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class QuestionGeneratedEvent:
    turn_index: int
    question: str
    intent: str
    expected_depth: str
    followup_hint: str | None
    should_end: bool


@dataclass(frozen=True, slots=True)
class ReferenceAnswerReadyEvent:
    turn_index: int
    answer_outline: tuple[str, ...]
    ideal_answer: str
    key_evaluation_points: tuple[str, ...]
    common_pitfalls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ObserverObservationEvent:
    turn_index: int
    observation: str
    tone: str
    actionable: bool


@dataclass(frozen=True, slots=True)
class TranscriptPartialEvent:
    turn_index: int
    text: str


@dataclass(frozen=True, slots=True)
class TranscriptFinalEvent:
    turn_index: int
    text: str


OrchestratorEvent = (
    TurnAssessedEvent
    | TurnCompressedEvent
    | QuestionGeneratedEvent
    | ReferenceAnswerReadyEvent
    | ObserverObservationEvent
    | TranscriptPartialEvent
    | TranscriptFinalEvent
)
