from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.orm import Task


class TaskRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, task_id: int) -> Task | None:
        return self._session.get(Task, task_id)

    def create(
        self,
        *,
        type: str,
        queue: str,
        payload: str,
        max_retries: int = 3,
    ) -> Task:
        task = Task(
            type=type,
            queue=queue,
            payload=payload,
            status="pending",
            max_retries=max_retries,
            retry_count=0,
        )
        self._session.add(task)
        self._session.commit()
        self._session.refresh(task)
        return task

    def update_status(
        self,
        task_id: int,
        status: str,
        *,
        error: str | None = None,
        increment_retry: bool = False,
    ) -> Task | None:
        task = self.get(task_id)
        if task is None:
            return None
        task.status = status
        task.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        if error is not None:
            task.error = error
        if increment_retry:
            task.retry_count += 1
        self._session.commit()
        self._session.refresh(task)
        return task

    def list_tasks(
        self,
        queue: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[Task]:
        query = self._session.query(Task)
        if queue:
            query = query.filter(Task.queue == queue)
        if status:
            query = query.filter(Task.status == status)
        return query.order_by(Task.created_at.desc()).limit(limit).all()

    def delete_old_completed(self, before: datetime) -> int:
        tasks = (
            self._session.query(Task)
            .filter(Task.status == "completed", Task.updated_at < before)
            .all()
        )
        count = len(tasks)
        for task in tasks:
            self._session.delete(task)
        self._session.commit()
        return count
