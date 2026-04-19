from __future__ import annotations

from uuid import UUID

from pydantic import Field

from app.models.enums import CandidateAssetStatus
from app.schemas.common import SchemaModel, TimestampedResponse
from app.schemas.parse import ParseResultPreview, ParseRequestResponse, ParseResultResponse


class AssetUploadResponse(TimestampedResponse):
    asset_bundle_id: UUID = Field(alias="id")
    status: CandidateAssetStatus
    uploaded_kind: str


class AssetUploadRequest(SchemaModel):
    asset_bundle_id: UUID | None = None


class CandidateAssetResponse(TimestampedResponse):
    user_id: UUID
    status: CandidateAssetStatus
    resume_filename: str | None = None
    jd_filename: str | None = None
    parse_preview: ParseResultPreview | None = None


__all__ = [
    "AssetUploadResponse",
    "CandidateAssetResponse",
    "ParseRequestResponse",
    "ParseResultResponse",
]
