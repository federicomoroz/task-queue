import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import SessionLocal, create_tables
from app.core.event_manager import EventManager
from app.controllers import tasks_controller, queues_controller
from app.controllers.tasks_controller import set_event_manager
from app.models.repositories.task_repository import TaskRepository
from app.models.services.log_listener import LogListener
from app.views.templates.spa import router as spa_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


def _purge_old_tasks() -> None:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(
        hours=settings.purge_completed_after_hours
    )
    session = SessionLocal()
    try:
        count = TaskRepository(session).delete_old_completed(cutoff)
        if count:
            logger.info("Purged %d completed tasks older than %dh", count, settings.purge_completed_after_hours)
    finally:
        session.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()

    event_manager = EventManager()
    LogListener(event_manager)
    set_event_manager(event_manager)

    scheduler = BackgroundScheduler()
    scheduler.add_job(_purge_old_tasks, "interval", hours=1)
    scheduler.start()

    logger.info("task-queue API started on port 8004")
    yield

    scheduler.shutdown(wait=False)
    logger.info("task-queue API shutting down")


app = FastAPI(
    title="task-queue",
    description="Distributed task queue with Redis broker and SQLite persistence",
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(spa_router)
app.include_router(tasks_controller.router)
app.include_router(queues_controller.router)


@app.get("/health", tags=["health"])
def health():
    return JSONResponse({"status": "ok"})
