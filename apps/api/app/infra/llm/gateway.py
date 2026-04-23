"""LLM gateway: BYOK + LiteLLM + tenacity.

Flow:
    caller -> BYOKGateway.complete(messages, response_model=...) -> litellm.acompletion
    upstream error -> mapped to LLM*Error -> caller only sees typed errors

Design notes:
- Gateway is constructed per-request from an LLMConfig. It holds the config by
  reference and nothing else; when the gateway goes out of scope so does the key.
- Retries are restricted to network / rate-limit errors. Auth errors never retry
  (no point) and content-safety errors never retry (user must change input).
- Provider-specific model routing is handled in `_resolve_model_ref` so the
  caller always sends plain model names (e.g. `deepseek-chat`) and we prepend
  the LiteLLM routing prefix (`openai/`) for OpenAI-compatible providers.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import litellm
from litellm.exceptions import (
    APIConnectionError,
    AuthenticationError,
    BadRequestError,
    ContentPolicyViolationError,
    RateLimitError,
    ServiceUnavailableError,
    Timeout,
)
from tenacity import (
    AsyncRetrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.infra.llm.config import LLMConfig
from app.infra.llm.errors import (
    LLMAuthError,
    LLMContentSafetyError,
    LLMError,
    LLMNetworkError,
    LLMRateLimitError,
)

_OPENAI_COMPATIBLE_PROVIDERS = frozenset(
    {"custom", "siliconflow", "deepseek", "dashscope", "openai"}
)


class LLMGateway(ABC):
    @abstractmethod
    async def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        """Send a chat-completion request and return the raw upstream response object."""


class BYOKGateway(LLMGateway):
    def __init__(self, config: LLMConfig) -> None:
        self._config = config

    async def complete(self, messages: list[dict[str, Any]], **kwargs: Any) -> Any:
        kwargs.setdefault("timeout", 30)
        model_ref = self._resolve_model_ref()

        async for attempt in AsyncRetrying(
            stop=stop_after_attempt(3),
            wait=wait_exponential(multiplier=0.5, min=0.5, max=4),
            retry=retry_if_exception_type((LLMNetworkError, LLMRateLimitError)),
            reraise=True,
        ):
            with attempt:
                try:
                    return await litellm.acompletion(
                        api_key=self._config.api_key.get_secret_value(),
                        base_url=self._config.base_url,
                        model=model_ref,
                        messages=messages,
                        **kwargs,
                    )
                except AuthenticationError as exc:
                    raise LLMAuthError(str(exc)) from exc
                except RateLimitError as exc:
                    raise LLMRateLimitError(str(exc)) from exc
                except ContentPolicyViolationError as exc:
                    raise LLMContentSafetyError(str(exc)) from exc
                except (APIConnectionError, Timeout, ServiceUnavailableError) as exc:
                    raise LLMNetworkError(str(exc)) from exc
                except BadRequestError as exc:
                    raise LLMError(str(exc)) from exc

        raise LLMError("LLM call exhausted retries without a result")

    def _resolve_model_ref(self) -> str:
        if self._config.provider in _OPENAI_COMPATIBLE_PROVIDERS:
            return f"openai/{self._config.model}"
        return self._config.model
