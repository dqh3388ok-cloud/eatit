from __future__ import annotations

from pydantic import BaseModel


class CompressionTurn(BaseModel):
    question: str
    answer: str


class CompressionAgentInput(BaseModel):
    previous_summary: str | None = None
    turns: list[CompressionTurn]


class CompressionAgentOutput(BaseModel):
    summary: str
    preserved_keywords: list[str]
    open_threads: list[str]
