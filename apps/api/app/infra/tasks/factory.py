from __future__ import annotations

from functools import lru_cache

from app.infra.tasks.asyncio_backend import AsyncioBackend
from app.infra.tasks.base import TaskQueueInterface


@lru_cache(maxsize=1)
def get_task_queue_backend() -> TaskQueueInterface:
    return AsyncioBackend()
