from __future__ import annotations

from pathlib import Path
from uuid import UUID

from fastapi import HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.parse.schemas import ParseAgentInput
from app.agents.parse.service import ParseAgentService
from app.api.dependencies.auth import AuthenticatedUser
from app.infra.llm import LLMGateway
from app.infra.storage import StorageInterface
from app.models.asset import CandidateAsset, ParseResult
from app.models.enums import CandidateAssetStatus, ParseResultStatus
from app.schemas.assets import AssetUploadResponse
from app.schemas.parse import (
    ParseRequestResponse,
    ParseResultPayload,
    ParseResultPreview,
    ParseResultResponse,
)


class AssetsService:
    async def upload_resume(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        storage: StorageInterface,
        file: UploadFile,
        asset_bundle_id: UUID | None,
    ) -> AssetUploadResponse:
        asset = await self._get_or_create_asset(session, current_user, asset_bundle_id)
        file_ref = await storage.upload(
            self._build_storage_key("resume", asset.id, file.filename),
            await file.read(),
        )
        asset.resume_filename = file.filename
        asset.resume_content_type = file.content_type
        asset.resume_file_ref = file_ref
        asset.status = self._derive_asset_status(asset)
        await session.commit()
        await session.refresh(asset)
        return AssetUploadResponse.model_validate(
            {
                **asset.__dict__,
                "asset_bundle_id": asset.id,
                "uploaded_kind": "resume",
            }
        )

    async def upload_jd(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        storage: StorageInterface,
        file: UploadFile,
        asset_bundle_id: UUID | None,
    ) -> AssetUploadResponse:
        asset = await self._get_or_create_asset(session, current_user, asset_bundle_id)
        file_ref = await storage.upload(
            self._build_storage_key("jd", asset.id, file.filename),
            await file.read(),
        )
        asset.jd_filename = file.filename
        asset.jd_content_type = file.content_type
        asset.jd_file_ref = file_ref
        asset.status = self._derive_asset_status(asset)
        await session.commit()
        await session.refresh(asset)
        return AssetUploadResponse.model_validate(
            {
                **asset.__dict__,
                "asset_bundle_id": asset.id,
                "uploaded_kind": "jd",
            }
        )

    async def trigger_parse(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        asset_bundle_id: UUID,
        gateway: LLMGateway,
        storage: StorageInterface,
    ) -> ParseRequestResponse:
        asset = await self._get_owned_asset(session, current_user, str(asset_bundle_id))
        if not asset.resume_file_ref or not asset.jd_file_ref:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Both resume and JD must be uploaded before parsing.",
            )

        resume_text = await self._download_as_text(storage, asset.resume_file_ref)
        jd_text = await self._download_as_text(storage, asset.jd_file_ref)

        agent_output = await ParseAgentService().run(
            ParseAgentInput(resume_text=resume_text, jd_text=jd_text),
            gateway,
        )
        payload = ParseResultPayload.model_validate(agent_output.model_dump())

        result = await session.execute(
            select(ParseResult).where(ParseResult.candidate_asset_id == asset.id)
        )
        parse_result = result.scalar_one_or_none()

        if parse_result is None:
            parse_result = ParseResult(
                candidate_asset_id=asset.id,
                status=ParseResultStatus.SUCCEEDED,
                payload=payload.model_dump(mode="json"),
                match_summary=payload.match_summary,
            )
            session.add(parse_result)
        else:
            parse_result.status = ParseResultStatus.SUCCEEDED
            parse_result.payload = payload.model_dump(mode="json")
            parse_result.match_summary = payload.match_summary

        asset.status = CandidateAssetStatus.ANALYSIS_READY
        await session.commit()

        return ParseRequestResponse(
            asset_bundle_id=asset.id,
            status=parse_result.status,
            payload=payload,
        )

    @staticmethod
    async def _download_as_text(storage: StorageInterface, file_ref: str) -> str:
        data = await storage.download(file_ref)
        # Best-effort UTF-8 decode. Phase 3 is text-first; PDF/doc
        # extraction is a follow-up concern that belongs in a parser
        # service, not here.
        return data.decode("utf-8", errors="replace")

    async def get_parse_result(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        asset_bundle_id: UUID,
    ) -> ParseResultResponse:
        asset = await self._get_owned_asset(session, current_user, str(asset_bundle_id))
        result = await session.execute(
            select(ParseResult).where(ParseResult.candidate_asset_id == asset.id)
        )
        parse_result = result.scalar_one_or_none()

        if parse_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Parse result not found.",
            )

        return ParseResultResponse(
            id=parse_result.id,
            created_at=parse_result.created_at,
            updated_at=parse_result.updated_at,
            candidate_asset_id=parse_result.candidate_asset_id,
            status=parse_result.status,
            payload=ParseResultPayload.model_validate(parse_result.payload),
        )

    async def get_asset_preview(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        asset_bundle_id: UUID,
    ) -> ParseResultPreview | None:
        asset = await self._get_owned_asset(session, current_user, str(asset_bundle_id))
        result = await session.execute(
            select(ParseResult).where(ParseResult.candidate_asset_id == asset.id)
        )
        parse_result = result.scalar_one_or_none()
        if parse_result is None:
            return None
        payload = ParseResultPayload.model_validate(parse_result.payload)
        return ParseResultPreview(
            match_summary=payload.match_summary,
            candidate_risk_count=len(payload.candidate_risks),
            project_hook_count=len(payload.project_hooks),
        )

    async def _get_owned_asset(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        asset_bundle_id: str,
    ) -> CandidateAsset:
        result = await session.execute(
            select(CandidateAsset).where(
                CandidateAsset.id == asset_bundle_id,
                CandidateAsset.user_id == current_user.id,
            )
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Asset bundle not found.",
            )
        return asset

    async def _get_or_create_asset(
        self,
        session: AsyncSession,
        current_user: AuthenticatedUser,
        asset_bundle_id: UUID | None,
    ) -> CandidateAsset:
        if asset_bundle_id is not None:
            return await self._get_owned_asset(session, current_user, str(asset_bundle_id))

        asset = CandidateAsset(user_id=current_user.id, status=CandidateAssetStatus.DRAFT)
        session.add(asset)
        await session.flush()
        return asset

    @staticmethod
    def _derive_asset_status(asset: CandidateAsset) -> CandidateAssetStatus:
        if asset.resume_file_ref and asset.jd_file_ref:
            return CandidateAssetStatus.READY_FOR_PARSE
        return CandidateAssetStatus.DRAFT

    @staticmethod
    def _build_storage_key(kind: str, asset_id: UUID, filename: str | None) -> str:
        safe_name = Path(filename or f"{kind}.txt").name
        return f"assets/{kind}/{asset_id}/{safe_name}"
