from fastapi import APIRouter

from app.core.config import settings
from app.models.services.queue_service import RedisQueueService
from app.views.schemas.task_schema import QueueOut

router = APIRouter(prefix="/queues", tags=["queues"])


@router.get("", response_model=list[QueueOut])
def list_queues():
    service = RedisQueueService()
    result = []
    for q in settings.queue_names:
        try:
            depth = service.depth(q)
        except Exception:
            depth = 0
        result.append(QueueOut(name=q, depth=depth))
    return result
