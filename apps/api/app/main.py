from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware.llm_config import LLMConfigMiddleware
from app.api.router import api_router
from app.infra.config import get_settings
from app.infra.logging import configure_logging, get_logger
from app.ws import router as ws_router

# Origins that may talk to the local backend during development.
# In `tauri dev` the webview loads from vite at :1420; the packaged app
# loads from `tauri://localhost`. We accept both plus 127.0.0.1 variants.
_DEV_ALLOWED_ORIGINS = [
    "http://localhost:1420",
    "http://127.0.0.1:1420",
    "tauri://localhost",
    "http://tauri.localhost",
    "https://tauri.localhost",
]

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
    # CORS first so preflight OPTIONS responses reach the browser before any
    # custom middleware short-circuits on header parsing.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_DEV_ALLOWED_ORIGINS,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )
    app.add_middleware(LLMConfigMiddleware)
    app.include_router(api_router)
    app.include_router(ws_router)
    return app


app = create_app()
