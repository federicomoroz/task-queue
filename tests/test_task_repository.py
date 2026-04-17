import json
from datetime import datetime, timedelta, timezone

import pytest

from app.models.repositories.task_repository import TaskRepository


def test_create_and_get(db_session):
    repo = TaskRepository(db_session)
    task = repo.create(type="echo", queue="default", payload=json.dumps({"msg": "hi"}))
    assert task.id is not None
    assert task.status == "pending"
    assert task.retry_count == 0

    fetched = repo.get(task.id)
    assert fetched.type == "echo"
    assert fetched.queue == "default"


def test_get_nonexistent(db_session):
    repo = TaskRepository(db_session)
    assert repo.get(9999) is None


def test_update_status(db_session):
    repo = TaskRepository(db_session)
    task = repo.create(type="echo", queue="default", payload="{}")
    updated = repo.update_status(task.id, "processing")
    assert updated.status == "processing"


def test_update_status_with_error(db_session):
    repo = TaskRepository(db_session)
    task = repo.create(type="echo", queue="default", payload="{}")
    updated = repo.update_status(task.id, "failed", error="timeout")
    assert updated.status == "failed"
    assert updated.error == "timeout"


def test_increment_retry(db_session):
    repo = TaskRepository(db_session)
    task = repo.create(type="echo", queue="default", payload="{}")
    updated = repo.update_status(task.id, "retrying", increment_retry=True)
    assert updated.retry_count == 1
    updated2 = repo.update_status(task.id, "retrying", increment_retry=True)
    assert updated2.retry_count == 2


def test_list_tasks_filter_by_queue(db_session):
    repo = TaskRepository(db_session)
    repo.create(type="echo", queue="high", payload="{}")
    repo.create(type="echo", queue="low", payload="{}")

    high = repo.list_tasks(queue="high")
    assert len(high) == 1
    assert high[0].queue == "high"


def test_list_tasks_filter_by_status(db_session):
    repo = TaskRepository(db_session)
    t = repo.create(type="echo", queue="default", payload="{}")
    repo.update_status(t.id, "completed")
    repo.create(type="echo", queue="default", payload="{}")

    completed = repo.list_tasks(status="completed")
    assert len(completed) == 1
    pending = repo.list_tasks(status="pending")
    assert len(pending) == 1


def test_delete_old_completed(db_session):
    repo = TaskRepository(db_session)
    t = repo.create(type="echo", queue="default", payload="{}")
    repo.update_status(t.id, "completed")

    # Force updated_at to old date
    from app.models.orm import Task
    db_session.query(Task).filter(Task.id == t.id).update(
        {"updated_at": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=25)}
    )
    db_session.commit()

    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=24)
    deleted = repo.delete_old_completed(cutoff)
    assert deleted == 1
    assert repo.get(t.id) is None
