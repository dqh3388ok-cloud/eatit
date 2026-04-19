from __future__ import annotations

from typing import Annotated, Literal
from uuid import UUID

from pydantic import Field, TypeAdapter

from app.schemas.common import SchemaModel
from app.schemas.turns import (
    CompressedTurnSummary,
    NormalizedQuestion,
    NormalizedUserAssessment,
    ReferenceAnswer,
)


class ClientAudioChunkEvent(SchemaModel):
    event: Literal["client.audio.chunk"]
    content_type: str | None = None


class ClientTurnEndEvent(SchemaModel):
    event: Literal["client.turn.end"]


class ClientSessionPauseEvent(SchemaModel):
    event: Literal["client.session.pause"]


class ClientSessionResumeEvent(SchemaModel):
    event: Literal["client.session.resume"]


class ClientSessionEndEvent(SchemaModel):
    event: Literal["client.session.end"]


ClientTextEvent = Annotated[
    ClientTurnEndEvent
    | ClientSessionPauseEvent
    | ClientSessionResumeEvent
    | ClientSessionEndEvent,
    Field(discriminator="event"),
]

ClientEvent = Annotated[
    ClientAudioChunkEvent | ClientTextEvent,
    Field(discriminator="event"),
]

CLIENT_TEXT_EVENT_ADAPTER = TypeAdapter(ClientTextEvent)
CLIENT_EVENT_ADAPTER = TypeAdapter(ClientEvent)


class ServerTranscriptPartialEvent(SchemaModel):
    event: Literal["server.transcript.partial"]
    payload: dict[str, str]


class ServerTranscriptFinalizedEvent(SchemaModel):
    event: Literal["server.transcript.finalized"]
    payload: dict[str, str]


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
    | ServerTranscriptFinalizedEvent
    | ServerTurnAssessedEvent
    | ServerTurnCompressedEvent
    | ServerQuestionGeneratedEvent
    | ServerReferenceReadyEvent
    | ServerSessionEndedEvent
    | ServerErrorEvent,
    Field(discriminator="event"),
]


SERVER_EVENT_ADAPTER = TypeAdapter(ServerEvent)
