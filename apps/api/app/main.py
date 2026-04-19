from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.infra.config import get_settings
from app.infra.logging import configure_logging, get_logger
from app.ws import router as ws_router

configure_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings = get_settings()
    logger.info(
        "app.startup",
        app_name=settings.app_name,
        app_env=settings.app_env,
        app_version=settings.app_version,
    )
    yield
    logger.info("app.shutdown", app_name=settings.app_name)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name, version=settings.app_version, lifespan=lifespan)
    app.include_router(api_router)
    app.include_router(ws_router)
    return app


app = create_app()
