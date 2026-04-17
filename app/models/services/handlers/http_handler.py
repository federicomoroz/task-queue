import json
import logging

import httpx

from app.models.orm import Task
from app.models.services.interfaces import TaskHandlerBase

logger = logging.getLogger(__name__)


class HttpHandler(TaskHandlerBase):
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def run(self, task: Task) -> None:
        payload = json.loads(task.payload)
        method: str = payload.get("method", "GET").upper()
        url: str = payload["url"]
        body: dict = payload.get("body", {})

        response = self._client.request(method, url, json=body or None, timeout=30)
        response.raise_for_status()
        logger.info(
            "[http_request] task_id=%d %s %s → %d",
            task.id,
            method,
            url,
            response.status_code,
        )
