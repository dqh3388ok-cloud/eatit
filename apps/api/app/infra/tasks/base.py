from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable


TaskFactory = Callable[[], Awaitable[None]]


class TaskQueueInterface(ABC):
    @abstractmethod
    async def enqueue(self, task_name: str, task_factory: TaskFactory) -> str:
        """Enqueue a fire-and-forget task and return its opaque task id."""
