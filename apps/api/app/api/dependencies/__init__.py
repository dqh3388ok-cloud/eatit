"""API dependency helpers."""

from app.api.dependencies.cache import get_cache
from app.api.dependencies.storage import get_storage

__all__ = ["get_cache", "get_storage"]
