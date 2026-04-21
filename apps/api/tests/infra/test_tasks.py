from __future__ import annotations

import anyio

from app.infra.tasks.asyncio_backend import AsyncioBackend


async def test_asyncio_backend_executes_enqueued_task() -> None:
    backend = AsyncioBackend()
    event = anyio.Event()
    state: dict[str, str] = {}

    async def job() -> None:
        state["status"] = "done"
        event.set()

    task_id = await backend.enqueue("test-job", job)

    assert task_id
    await event.wait()
    assert state["status"] == "done"
