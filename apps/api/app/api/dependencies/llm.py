"""FastAPI dependencies for the LLM layer."""

from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.infra.llm import LLMConfig, LLMGateway, build_gateway

_MISSING_DETAIL = "Missing X-LLM-Config header."


def get_llm_config(request: Request) -> LLMConfig:
    config = getattr(request.state, "llm_config", None)
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_MISSING_DETAIL,
        )
    return config


def get_llm_gateway(request: Request) -> LLMGateway:
    return build_gateway(get_llm_config(request))
