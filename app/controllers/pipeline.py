import json
import logging

from app.core.event_manager import EventManager
from app.core import events
from app.models.orm import Task
from app.models.repositories.task_repository import TaskRepository
from app.models.services.interfaces import QueueServiceBase

logger = logging.getLogger(__name__)

KNOWN_TYPES = {"echo", "http_request"}


class ValidateStep:
    """Rejects unknown task types early."""

    def process(self, task_type: str) -> None:
        if task_type not in KNOWN_TYPES:
            raise ValueError(f"Unknown task type: {task_type!r}. Known: {KNOWN_TYPES}")


class EnqueueStep:
    """Persists task in DB and pushes task_id to Redis queue."""

    def __init__(
        self,
        repo: TaskRepository,
        queue_service: QueueServiceBase,
        event_manager: EventManager,
    ) -> None:
        self._repo = repo
        self._queue_service = queue_service
        self._event_manager = event_manager

    def process(
        self, *, type: str, queue: str, payload: dict, max_retries: int
    ) -> Task:
        task = self._repo.create(
            type=type,
            queue=queue,
            payload=json.dumps(payload),
            max_retries=max_retries,
        )
        self._queue_service.push(queue, task.id)
        self._event_manager.emit(
            events.TASK_ENQUEUED,
            task_id=task.id,
            queue=queue,
            task_type=type,
        )
        return task


class TaskPipeline:
    def __init__(
        self,
        repo: TaskRepository,
        queue_service: QueueServiceBase,
        event_manager: EventManager,
    ) -> None:
        self._validate = ValidateStep()
        self._enqueue = EnqueueStep(repo, queue_service, event_manager)

    def run(
        self, *, type: str, queue: str, payload: dict, max_retries: int = 3
    ) -> Task:
        self._validate.process(type)
        return self._enqueue.process(
            type=type, queue=queue, payload=payload, max_retries=max_retries
        )
