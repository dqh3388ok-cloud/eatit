"""LLMConfig value object — carries BYOK secrets for the duration of a single request.

Hard invariants (per Phase 3 architecture decisions):
- `api_key` is stored as `SecretStr` and is never rendered by the default repr.
- `__repr__` and `__str__` are overridden to guarantee no accidental leakage
  into str-formatted logs, tracebacks, or Sentry breadcrumbs.
- The model is `frozen=True`: once constructed it cannot be mutated, so no path
  exists for business code to "upgrade" a config in place.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr


class LLMConfig(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    provider: str
    api_key: SecretStr
    model: str
    base_url: str | None = None

    def __repr__(self) -> str:
        return (
            f"LLMConfig(provider={self.provider!r}, "
            f"model={self.model!r}, "
            f"base_url={self.base_url!r}, "
            "api_key=***)"
        )

    def __str__(self) -> str:
        return repr(self)
