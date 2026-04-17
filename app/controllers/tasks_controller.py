from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

import app.core.database as _db_mod
from app.core.event_manager import EventManager
from app.controllers.pipeline import TaskPipeline
from app.models.repositories.task_repository import TaskRepository
from app.models.services.queue_service import RedisQueueService
from app.views.schemas.task_schema import TaskIn, TaskOut

router = APIRouter(prefix="/tasks", tags=["tasks"])

_event_manager: EventManager | None = None


def set_event_manager(em: EventManager) -> None:
    global _event_manager
    _event_manager = em


def _get_session() -> Session:
    session = _db_mod.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@router.post("", response_model=TaskOut, status_code=202)
def create_task(
    body: TaskIn,
    session: Session = Depends(_get_session),
):
    repo = TaskRepository(session)
    queue_service = RedisQueueService()
    pipeline = TaskPipeline(repo, queue_service, _event_manager)
    try:
        task = pipeline.run(
            type=body.type,
            queue=body.queue,
            payload=body.payload,
            max_retries=body.max_retries,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return task


@router.get("", response_model=list[TaskOut])
def list_tasks(
    queue: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    session: Session = Depends(_get_session),
):
    repo = TaskRepository(session)
    return repo.list_tasks(queue=queue, status=status, limit=limit)


@router.get("/{task_id}", response_model=TaskOut)
def get_task(task_id: int, session: Session = Depends(_get_session)):
    repo = TaskRepository(session)
    task = repo.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task
