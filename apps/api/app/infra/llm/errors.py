"""Typed LLM errors.

Business code should only catch these, never the raw LiteLLM / httpx exceptions.
The gateway is the boundary that translates upstream exceptions into this hierarchy.
"""

from __future__ import annotations


class LLMError(Exception):
    """Base for all LLM gateway failures."""


class LLMAuthError(LLMError):
    """Upstream rejected the API key (401 / invalid key)."""


class LLMRateLimitError(LLMError):
    """Upstream returned 429 / quota exhausted."""


class LLMNetworkError(LLMError):
    """Connection, timeout, or transient 5xx from upstream."""


class LLMContentSafetyError(LLMError):
    """Upstream refused the request on content-safety grounds."""
