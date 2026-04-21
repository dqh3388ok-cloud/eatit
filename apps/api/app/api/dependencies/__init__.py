"""API dependency helpers."""

from app.api.dependencies.cache import get_cache
from app.api.dependencies.storage import get_storage
from app.api.dependencies.tasks import get_task_queue

__all__ = ["get_cache", "get_storage", "get_task_queue"]
