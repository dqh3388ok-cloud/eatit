from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    ContentPolicyViolationError,
    RateLimitError,
    Timeout,
)

from app.infra.llm import (
    BYOKGateway,
    LLMAuthError,
    LLMConfig,
    LLMContentSafetyError,
    LLMNetworkError,
    LLMRateLimitError,
    build_gateway,
)


SECRET = "sk-do-not-leak-39f4a"


def _config(**overrides):
    data = {
        "provider": "openai",
        "api_key": SECRET,
        "model": "gpt-4o-mini",
        "base_url": None,
    }
    data.update(overrides)
    return LLMConfig(**data)


def test_config_repr_and_str_mask_api_key() -> None:
    config = _config()

    assert SECRET not in repr(config)
    assert SECRET not in str(config)
    assert "***" in repr(config)


def test_config_secret_str_retrievable_only_via_get_secret_value() -> None:
    config = _config()

    # Pydantic SecretStr also masks on its own __repr__
    assert SECRET not in repr(config.api_key)
    assert config.api_key.get_secret_value() == SECRET


def test_config_is_frozen() -> None:
    config = _config()
    with pytest.raises(Exception):
        config.api_key = "another"  # type: ignore[misc]


def test_build_gateway_returns_byok() -> None:
    gateway = build_gateway(_config())

    assert isinstance(gateway, BYOKGateway)


@pytest.mark.parametrize(
    "provider,expected_prefix",
    [
        ("openai", "openai/"),
        ("siliconflow", "openai/"),
        ("deepseek", "openai/"),
        ("dashscope", "openai/"),
        ("custom", "openai/"),
        ("anthropic", ""),
    ],
)
def test_gateway_resolves_model_ref_for_openai_compatible_providers(
    provider: str, expected_prefix: str
) -> None:
    gateway = BYOKGateway(_config(provider=provider, model="claude-3-opus"))

    ref = gateway._resolve_model_ref()

    assert ref.startswith(expected_prefix)
    assert ref.endswith("claude-3-opus")


async def test_gateway_maps_authentication_error() -> None:
    gateway = BYOKGateway(_config())

    with patch(
        "app.infra.llm.gateway.litellm.acompletion",
        new=AsyncMock(
            side_effect=AuthenticationError(
                message="bad key",
                llm_provider="openai",
                model="gpt-4o-mini",
            )
        ),
    ):
        with pytest.raises(LLMAuthError):
            await gateway.complete([{"role": "user", "content": "hi"}])


async def test_gateway_maps_content_safety_error() -> None:
    gateway = BYOKGateway(_config())

    with patch(
        "app.infra.llm.gateway.litellm.acompletion",
        new=AsyncMock(
            side_effect=ContentPolicyViolationError(
                message="refused",
                llm_provider="openai",
                model="gpt-4o-mini",
            )
        ),
    ):
        with pytest.raises(LLMContentSafetyError):
            await gateway.complete([{"role": "user", "content": "hi"}])


async def test_gateway_retries_rate_limit_and_succeeds() -> None:
    gateway = BYOKGateway(_config())
    first = RateLimitError(message="429", llm_provider="openai", model="gpt-4o-mini")
    call_count = {"n": 0}

    async def flaky(*_args, **_kwargs):
        call_count["n"] += 1
        if call_count["n"] < 2:
            raise first
        return {"choices": [{"message": {"content": "ok"}}], "usage": {"prompt_tokens": 5, "completion_tokens": 1}}

    with patch("app.infra.llm.gateway.litellm.acompletion", new=flaky):
        result = await gateway.complete([{"role": "user", "content": "hi"}])

    assert call_count["n"] == 2
    assert result["usage"]["completion_tokens"] == 1


async def test_gateway_retries_network_error_then_raises() -> None:
    gateway = BYOKGateway(_config())
    net_err = APIConnectionError(message="boom", llm_provider="openai", model="gpt-4o-mini")

    with patch(
        "app.infra.llm.gateway.litellm.acompletion",
        new=AsyncMock(side_effect=net_err),
    ) as mock_call:
        with pytest.raises(LLMNetworkError):
            await gateway.complete([{"role": "user", "content": "hi"}])

    # Default tenacity config: 3 attempts
    assert mock_call.call_count == 3


async def test_gateway_does_not_retry_auth_error() -> None:
    gateway = BYOKGateway(_config())
    auth_err = AuthenticationError(
        message="bad", llm_provider="openai", model="gpt-4o-mini"
    )

    with patch(
        "app.infra.llm.gateway.litellm.acompletion",
        new=AsyncMock(side_effect=auth_err),
    ) as mock_call:
        with pytest.raises(LLMAuthError):
            await gateway.complete([{"role": "user", "content": "hi"}])

    assert mock_call.call_count == 1


async def test_gateway_passes_api_key_through_to_litellm() -> None:
    gateway = BYOKGateway(_config())

    captured: dict = {}

    async def capture(*_args, **kwargs):
        captured.update(kwargs)
        return {"usage": {"prompt_tokens": 1, "completion_tokens": 1}}

    with patch("app.infra.llm.gateway.litellm.acompletion", new=capture):
        await gateway.complete([{"role": "user", "content": "hi"}])

    assert captured["api_key"] == SECRET
    assert captured["model"] == "openai/gpt-4o-mini"
    assert captured["base_url"] is None


async def test_gateway_timeout_maps_to_network_error() -> None:
    gateway = BYOKGateway(_config())
    timeout = Timeout(message="slow", llm_provider="openai", model="gpt-4o-mini")

    with patch(
        "app.infra.llm.gateway.litellm.acompletion",
        new=AsyncMock(side_effect=timeout),
    ):
        with pytest.raises(LLMNetworkError):
            await gateway.complete([{"role": "user", "content": "hi"}])
