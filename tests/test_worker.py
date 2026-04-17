import json
from unittest.mock import MagicMock

import pytest

from app.core.event_manager import EventManager
from app.core import events
from app.models.orm import Task
from app.models.repositories.task_repository import TaskRepository
from app.models.services.interfaces import TaskHandlerBase
from app.models.services.queue_service import RedisQueueService
from worker.main import process_task


def make_task(db_session, **kwargs) -> Task:
    defaults = dict(type="echo", queue="default", payload="{}", max_retries=3)
    defaults.update(kwargs)
    repo = TaskRepository(db_session)
    return repo.create(**defaults)


def test_successful_task(db_session, fake_redis):
    task = make_task(db_session)
    repo = TaskRepository(db_session)
    em = EventManager()
    queue_service = RedisQueueService()

    completed_events = []
    em.subscribe(events.TASK_COMPLETED, lambda **kw: completed_events.append(kw))

    handler = MagicMock(spec=TaskHandlerBase)
    registry = {"echo": handler}

    process_task(task, repo, registry, em, queue_service)

    handler.run.assert_called_once_with(task)
    updated = repo.get(task.id)
    assert updated.status == "completed"
    assert len(completed_events) == 1
    assert completed_events[0]["task_id"] == task.id


def test_task_retried_on_failure(db_session, fake_redis):
    task = make_task(db_session, max_retries=3)
    repo = TaskRepository(db_session)
    em = EventManager()
    queue_service = RedisQueueService()

    failed_events = []
    em.subscribe(events.TASK_FAILED, lambda **kw: failed_events.append(kw))

    handler = MagicMock(spec=TaskHandlerBase)
    handler.run.side_effect = RuntimeError("transient error")
    registry = {"echo": handler}

    process_task(task, repo, registry, em, queue_service)

    updated = repo.get(task.id)
    assert updated.status == "retrying"
    assert updated.retry_count == 1
    assert updated.error == "transient error"
    # Should be re-enqueued
    assert queue_service.depth("default") == 1
    assert failed_events[0]["final"] is False


def test_task_fails_after_max_retries(db_session, fake_redis):
    task = make_task(db_session, max_retries=1)
    repo = TaskRepository(db_session)
    em = EventManager()
    queue_service = RedisQueueService()

    # Simulate task already attempted once
    repo.update_status(task.id, "retrying", increment_retry=True)
    task = repo.get(task.id)  # refresh

    failed_events = []
    em.subscribe(events.TASK_FAILED, lambda **kw: failed_events.append(kw))

    handler = MagicMock(spec=TaskHandlerBase)
    handler.run.side_effect = RuntimeError("permanent error")
    registry = {"echo": handler}

    process_task(task, repo, registry, em, queue_service)

    updated = repo.get(task.id)
    assert updated.status == "failed"
    assert updated.error == "permanent error"
    # Should NOT be re-enqueued
    assert queue_service.depth("default") == 0
    assert failed_events[0]["final"] is True


def test_unknown_handler_marks_failed(db_session, fake_redis):
    task = make_task(db_session, type="unknown_type")
    repo = TaskRepository(db_session)
    em = EventManager()
    queue_service = RedisQueueService()

    failed_events = []
    em.subscribe(events.TASK_FAILED, lambda **kw: failed_events.append(kw))

    process_task(task, repo, {}, em, queue_service)

    updated = repo.get(task.id)
    assert updated.status == "failed"
    assert len(failed_events) == 1
    assert failed_events[0]["final"] is True
