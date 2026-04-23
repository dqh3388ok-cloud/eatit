"""ASRConfig — carries the Azure Speech subscription_key + region.

The secret is stored as `SecretStr` and masked in `__repr__` / `__str__` so
stray log formatting cannot leak it. `frozen=True` prevents post-construction
mutation.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr


class ASRConfig(BaseModel):
    model_config = ConfigDict(frozen=True, str_strip_whitespace=True)

    provider: str = "azure"
    subscription_key: SecretStr
    region: str
    language: str = "zh-CN"

    def __repr__(self) -> str:
        return (
            f"ASRConfig(provider={self.provider!r}, "
            f"region={self.region!r}, "
            f"language={self.language!r}, "
            "subscription_key=***)"
        )

    def __str__(self) -> str:
        return repr(self)
