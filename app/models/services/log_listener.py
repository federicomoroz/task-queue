import logging

import app.core.database as _db_mod
from app.core.event_manager import EventManager
from app.core import events
from app.models.repositories.task_repository import TaskRepository

logger = logging.getLogger(__name__)


class LogListener:
    def __init__(self, event_manager: EventManager) -> None:
        event_manager.subscribe(events.TASK_ENQUEUED, self._on_enqueued)
        event_manager.subscribe(events.TASK_COMPLETED, self._on_completed)
        event_manager.subscribe(events.TASK_FAILED, self._on_failed)

    def _on_enqueued(self, *, task_id: int, queue: str, task_type: str) -> None:
        logger.info("Task %d enqueued → queue=%s type=%s", task_id, queue, task_type)

    def _on_completed(
        self, *, task_id: int, queue: str, task_type: str, duration_ms: float
    ) -> None:
        logger.info(
            "Task %d completed in %.0fms → queue=%s type=%s",
            task_id,
            duration_ms,
            queue,
            task_type,
        )
        self._update_status(task_id, "completed")

    def _on_failed(
        self,
        *,
        task_id: int,
        queue: str,
        task_type: str,
        error: str,
        final: bool,
    ) -> None:
        level = "FINAL" if final else "retrying"
        logger.warning(
            "Task %d failed [%s] → queue=%s type=%s error=%s",
            task_id,
            level,
            queue,
            task_type,
            error,
        )
        if final:
            self._update_status(task_id, "failed", error=error)

    def _update_status(
        self, task_id: int, status: str, *, error: str | None = None
    ) -> None:
        session = _db_mod.SessionLocal()
        try:
            repo = TaskRepository(session)
            repo.update_status(task_id, status, error=error)
        except Exception as exc:
            logger.error("LogListener DB update failed: %s", exc)
        finally:
            session.close()
