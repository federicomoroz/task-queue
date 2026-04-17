import pytest

from app.models.services.queue_service import RedisQueueService, QUEUE_PREFIX


def test_push_and_depth(fake_redis):
    svc = RedisQueueService()
    svc.push("default", 1)
    svc.push("default", 2)
    assert svc.depth("default") == 2


def test_pop_returns_task_id(fake_redis):
    svc = RedisQueueService()
    svc.push("default", 42)
    result = svc.pop(["default"], timeout=1)
    assert result is not None
    queue, task_id = result
    assert queue == "default"
    assert task_id == 42


def test_pop_empty_returns_none(fake_redis):
    svc = RedisQueueService()
    result = svc.pop(["default"], timeout=1)
    assert result is None


def test_pop_drains_lifo_order(fake_redis):
    """BRPOP (right pop) means first-pushed is consumed first (FIFO with LPUSH)."""
    svc = RedisQueueService()
    svc.push("default", 10)
    svc.push("default", 20)
    _, first = svc.pop(["default"], timeout=1)
    _, second = svc.pop(["default"], timeout=1)
    assert first == 10
    assert second == 20


def test_depth_empty(fake_redis):
    svc = RedisQueueService()
    assert svc.depth("missing") == 0


def test_key_schema(fake_redis):
    svc = RedisQueueService()
    svc.push("high", 1)
    assert fake_redis.llen(f"{QUEUE_PREFIX}high") == 1
