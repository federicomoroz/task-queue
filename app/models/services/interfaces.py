from abc import ABC, abstractmethod

from app.models.orm import Task


class TaskHandlerBase(ABC):
    @abstractmethod
    def run(self, task: Task) -> None: ...


class QueueServiceBase(ABC):
    @abstractmethod
    def push(self, queue: str, task_id: int) -> None: ...

    @abstractmethod
    def pop(self, queues: list[str], timeout: int = 5) -> tuple[str, int] | None: ...

    @abstractmethod
    def depth(self, queue: str) -> int: ...
