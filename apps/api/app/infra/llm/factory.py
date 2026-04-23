"""Gateway factory — one function, zero caching.

BYOK gateways are cheap (just hold an LLMConfig reference) so we rebuild them
per request. Caching by config would tempt us to put the key into a cache key,
which is precisely what we are avoiding.
"""

from __future__ import annotations

from app.infra.llm.config import LLMConfig
from app.infra.llm.gateway import BYOKGateway, LLMGateway


def build_gateway(config: LLMConfig) -> LLMGateway:
    return BYOKGateway(config)
