import json
import logging
import time

from app.models.orm import Task
from app.models.services.interfaces import TaskHandlerBase

logger = logging.getLogger(__name__)


class EchoHandler(TaskHandlerBase):
    def run(self, task: Task) -> None:
        payload = json.loads(task.payload)
        msg = payload.get("msg", "")
        logger.info("[echo] task_id=%d msg=%r", task.id, msg)
        time.sleep(1)
