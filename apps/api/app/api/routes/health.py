from fastapi import APIRouter
from pydantic import BaseModel

from app.infra.config import get_settings


class HealthResponse(BaseModel):
    status: str
    version: str


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", version=settings.app_version)
