import app.core.redis_client as _redis_mod
from app.models.services.interfaces import QueueServiceBase

QUEUE_PREFIX = "tq:queue:"


class RedisQueueService(QueueServiceBase):
    def _key(self, queue: str) -> str:
        return f"{QUEUE_PREFIX}{queue}"

    def push(self, queue: str, task_id: int) -> None:
        _redis_mod.get_redis().lpush(self._key(queue), str(task_id))

    def pop(self, queues: list[str], timeout: int = 5) -> tuple[str, int] | None:
        keys = [self._key(q) for q in queues]
        result = _redis_mod.get_redis().brpop(keys, timeout=timeout)
        if result is None:
            return None
        key, value = result
        queue_name = key.removeprefix(QUEUE_PREFIX)
        return queue_name, int(value)

    def depth(self, queue: str) -> int:
        return _redis_mod.get_redis().llen(self._key(queue))
