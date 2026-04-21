from __future__ import annotations

import asyncio
from collections.abc import Awaitable
from collections.abc import Callable

import uuid_utils as uuid7_utils

from app.infra.tasks.base import TaskFactory, TaskQueueInterface


class AsyncioBackend(TaskQueueInterface):
    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task[None]] = {}

    async def enqueue(self, task_name: str, task_factory: TaskFactory) -> str:
        task_id = str(uuid7_utils.uuid7())
        loop = asyncio.get_running_loop()
        task = loop.create_task(self._run_task(task_name, task_factory), name=task_name)
        self._tasks[task_id] = task
        task.add_done_callback(lambda _: self._tasks.pop(task_id, None))
        return task_id

    async def _run_task(self, task_name: str, task_factory: TaskFactory) -> None:
        coroutine = task_factory()
        try:
            await coroutine
        except Exception as exc:  # pragma: no cover - asyncio keeps traceback on the task
            setattr(exc, "__task_name__", task_name)
            raise
