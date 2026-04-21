from app.infra.tasks import TaskQueueInterface, get_task_queue_backend


def get_task_queue() -> TaskQueueInterface:
    # Business services depend on the interface, not the asyncio backend.
    return get_task_queue_backend()
