"""
Worker process: BRPOP from Redis → run handler → update DB status.
Scalable: multiple containers can run this concurrently.
"""
import logging
import time

import httpx

from app.core.config import settings
from app.core.database import SessionLocal, create_tables
from app.core.event_manager import EventManager
from app.core import events
from app.models.orm import Task
from app.models.repositories.task_repository import TaskRepository
from app.models.services.interfaces import TaskHandlerBase
from app.models.services.queue_service import RedisQueueService
from app.models.services.handlers.echo_handler import EchoHandler
from app.models.services.handlers.http_handler import HttpHandler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def build_handler_registry(http_client: httpx.Client) -> dict[str, TaskHandlerBase]:
    return {
        "echo": EchoHandler(),
        "http_request": HttpHandler(http_client),
    }


def process_task(
    task: Task,
    repo: TaskRepository,
    handler_registry: dict[str, TaskHandlerBase],
    event_manager: EventManager,
    queue_service: RedisQueueService,
) -> None:
    repo.update_status(task.id, "processing")
    handler = handler_registry.get(task.type)
    if handler is None:
        repo.update_status(task.id, "failed", error=f"No handler for type {task.type!r}")
        event_manager.emit(
            events.TASK_FAILED,
            task_id=task.id,
            queue=task.queue,
            task_type=task.type,
            error=f"No handler for type {task.type!r}",
            final=True,
        )
        return

    start = time.monotonic()
    try:
        handler.run(task)
        duration_ms = (time.monotonic() - start) * 1000
        repo.update_status(task.id, "completed")
        event_manager.emit(
            events.TASK_COMPLETED,
            task_id=task.id,
            queue=task.queue,
            task_type=task.type,
            duration_ms=duration_ms,
        )
    except Exception as exc:
        error_msg = str(exc)
        if task.retry_count < task.max_retries:
            repo.update_status(
                task.id, "retrying", error=error_msg, increment_retry=True
            )
            queue_service.push(task.queue, task.id)
            event_manager.emit(
                events.TASK_FAILED,
                task_id=task.id,
                queue=task.queue,
                task_type=task.type,
                error=error_msg,
                final=False,
            )
            logger.warning(
                "Task %d re-enqueued (attempt %d/%d)",
                task.id,
                task.retry_count + 1,
                task.max_retries,
            )
        else:
            repo.update_status(task.id, "failed", error=error_msg)
            event_manager.emit(
                events.TASK_FAILED,
                task_id=task.id,
                queue=task.queue,
                task_type=task.type,
                error=error_msg,
                final=True,
            )


def run(stop_event=None) -> None:
    """
    Main worker loop.
    stop_event: optional threading.Event; when set, the loop exits cleanly.
    """
    import threading
    if stop_event is None:
        stop_event = threading.Event()

    create_tables()

    event_manager = EventManager()
    queue_service = RedisQueueService()
    http_client = httpx.Client()
    handler_registry = build_handler_registry(http_client)
    queue_names = settings.queue_names

    logger.info("Worker started. Listening on queues: %s", queue_names)

    try:
        while not stop_event.is_set():
            try:
                result = queue_service.pop(queue_names, timeout=settings.brpop_timeout)
            except Exception as exc:
                logger.warning("Redis pop error (will retry): %s", exc)
                stop_event.wait(timeout=5)
                continue
            if result is None:
                continue

            _, task_id = result
            session = SessionLocal()
            try:
                repo = TaskRepository(session)
                task = repo.get(task_id)
                if task is None:
                    logger.warning("Task %d not found in DB, skipping", task_id)
                    continue
                process_task(task, repo, handler_registry, event_manager, queue_service)
            except Exception as exc:
                logger.error("Unexpected error processing task %d: %s", task_id, exc)
            finally:
                session.close()
    finally:
        http_client.close()
        logger.info("Worker stopped")


if __name__ == "__main__":
    run()
