from fastapi import APIRouter

from app.core.config import settings
from app.models.services.queue_service import RedisQueueService
from app.views.schemas.task_schema import QueueOut

router = APIRouter(prefix="/queues", tags=["queues"])


@router.get("", response_model=list[QueueOut])
def list_queues():
    service = RedisQueueService()
    return [
        QueueOut(name=q, depth=service.depth(q)) for q in settings.queue_names
    ]
