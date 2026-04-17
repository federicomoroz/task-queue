import json

import pytest

from app.controllers.pipeline import TaskPipeline, ValidateStep
from app.core.event_manager import EventManager
from app.models.repositories.task_repository import TaskRepository
from app.models.services.queue_service import RedisQueueService


def test_validate_step_rejects_unknown_type():
    step = ValidateStep()
    with pytest.raises(ValueError, match="Unknown task type"):
        step.process("nonexistent_type")


def test_validate_step_accepts_known_types():
    step = ValidateStep()
    step.process("echo")
    step.process("http_request")


def test_pipeline_creates_task_and_enqueues(db_session, fake_redis):
    repo = TaskRepository(db_session)
    queue_service = RedisQueueService()
    em = EventManager()
    pipeline = TaskPipeline(repo, queue_service, em)

    task = pipeline.run(type="echo", queue="default", payload={"msg": "test"})

    assert task.id is not None
    assert task.status == "pending"
    assert task.queue == "default"
    assert json.loads(task.payload) == {"msg": "test"}
    assert queue_service.depth("default") == 1


def test_pipeline_emits_task_enqueued(db_session, fake_redis):
    repo = TaskRepository(db_session)
    queue_service = RedisQueueService()
    em = EventManager()

    received = []
    from app.core import events
    em.subscribe(events.TASK_ENQUEUED, lambda **kw: received.append(kw))

    pipeline = TaskPipeline(repo, queue_service, em)
    task = pipeline.run(type="echo", queue="high", payload={})

    assert len(received) == 1
    assert received[0]["task_id"] == task.id
    assert received[0]["queue"] == "high"
    assert received[0]["task_type"] == "echo"


def test_pipeline_rejects_unknown_type_end_to_end(db_session, fake_redis):
    repo = TaskRepository(db_session)
    queue_service = RedisQueueService()
    em = EventManager()
    pipeline = TaskPipeline(repo, queue_service, em)

    with pytest.raises(ValueError):
        pipeline.run(type="bad_type", queue="default", payload={})

    # Nothing should be in DB or Redis
    assert repo.list_tasks() == []
    assert queue_service.depth("default") == 0
