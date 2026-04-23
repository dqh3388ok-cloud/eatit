from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter

from app.infra.llm import LLMConfig
from app.schemas.common import SchemaModel
from app.schemas.turns import (
    CompressedTurnSummary,
    NormalizedQuestion,
    NormalizedUserAssessment,
    ReferenceAnswer,
)


class ClientSessionInitEvent(SchemaModel):
    """First frame the client must send after WS connect.

    Carries the BYOK config so the backend can build a per-session gateway.
    Arrives as a LiteLLM-compatible dict that Pydantic validates into
    `LLMConfig`; the secret never touches the DB or logs.
    """

    event: Literal["client.session.init"]
    config: LLMConfig


class ClientTurnStartEvent(SchemaModel):
    event: Literal["client.turn.start"]


class ClientTurnEndEvent(SchemaModel):
    event: Literal["client.turn.end"]
    question: str
    answer: str
    turn_index: int = Field(ge=0)


class ClientAudioStartEvent(SchemaModel):
    """Signals the beginning of a voice turn. The next binary frames up until
    `client.audio.stop` are streamed to the ASR backend as opus/webm chunks."""

    event: Literal["client.audio.start"]
    turn_index: int = Field(ge=0)


class ClientAudioStopEvent(SchemaModel):
    """Signals the end of a voice turn. The backend flushes the ASR stream and
    emits the final transcript as `server.transcript.final`."""

    event: Literal["client.audio.stop"]
    turn_index: int = Field(ge=0)


class ClientSessionPauseEvent(SchemaModel):
    event: Literal["client.session.pause"]


class ClientSessionResumeEvent(SchemaModel):
    event: Literal["client.session.resume"]


class ClientSessionEndEvent(SchemaModel):
    event: Literal["client.session.end"]


ClientTextEvent = Annotated[
    ClientSessionInitEvent
    | ClientTurnStartEvent
    | ClientTurnEndEvent
    | ClientAudioStartEvent
    | ClientAudioStopEvent
    | ClientSessionPauseEvent
    | ClientSessionResumeEvent
    | ClientSessionEndEvent,
    Field(discriminator="event"),
]


CLIENT_TEXT_EVENT_ADAPTER = TypeAdapter(ClientTextEvent)


class TranscriptPayload(SchemaModel):
    turn_index: int
    text: str


class ServerTranscriptPartialEvent(SchemaModel):
    event: Literal["server.transcript.partial"]
    payload: TranscriptPayload


class ServerTranscriptFinalEvent(SchemaModel):
    event: Literal["server.transcript.final"]
    payload: TranscriptPayload


class ServerTurnAssessedEvent(SchemaModel):
    event: Literal["server.turn.assessed"]
    payload: NormalizedUserAssessment


class ServerTurnCompressedEvent(SchemaModel):
    event: Literal["server.turn.compressed"]
    payload: CompressedTurnSummary


class ServerQuestionGeneratedEvent(SchemaModel):
    event: Literal["server.question.generated"]
    payload: NormalizedQuestion


class ServerReferenceReadyEvent(SchemaModel):
    event: Literal["server.reference.ready"]
    payload: ReferenceAnswer


class CoachObservation(SchemaModel):
    turn_index: int
    observation: str
    tone: Literal["support", "alert", "pivot"]
    actionable: bool


class ServerCoachObservationEvent(SchemaModel):
    event: Literal["server.coach.observation"]
    payload: CoachObservation


class ServerSessionEndedEvent(SchemaModel):
    event: Literal["server.session.ended"]
    payload: dict[str, str | UUID]


class ServerErrorEvent(SchemaModel):
    event: Literal["server.error"]
    code: str
    message: str
    recoverable: bool


ServerEvent = Annotated[
    ServerTranscriptPartialEvent
    | ServerTranscriptFinalEvent
    | ServerTurnAssessedEvent
    | ServerTurnCompressedEvent
    | ServerQuestionGeneratedEvent
    | ServerReferenceReadyEvent
    | ServerCoachObservationEvent
    | ServerSessionEndedEvent
    | ServerErrorEvent,
    Field(discriminator="event"),
]


SERVER_EVENT_ADAPTER = TypeAdapter(ServerEvent)
