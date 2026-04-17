import json
import logging
import threading
import time
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import httpx
from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import SessionLocal, create_tables
from app.core.event_manager import EventManager
from app.controllers import tasks_controller, queues_controller
from app.controllers.tasks_controller import set_event_manager
from app.models.repositories.task_repository import TaskRepository
from app.models.services.handlers.echo_handler import EchoHandler
from app.models.services.handlers.http_handler import HttpHandler
from app.models.services.log_listener import LogListener
from app.views.templates.spa import router as spa_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

_worker_stop = threading.Event()

# Handler registry shared between inline worker and daemon thread worker
_http_client = httpx.Client()
_HANDLER_REGISTRY = {
    "echo": EchoHandler(),
    "http_request": HttpHandler(_http_client),
}


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


def _process_pending_tasks() -> None:
    """Inline worker: pick up any 'pending' tasks and process them directly.
    Runs every 3 s via APScheduler as a fallback when the Redis worker can't connect.
    """
    session = SessionLocal()
    try:
        repo = TaskRepository(session)
        pending = repo.list_tasks(status="pending", limit=5)
        for task in pending:
            # Claim the task (mark as processing) to avoid double-processing
            repo.update_status(task.id, "processing")
            session.expire_all()  # reload from DB

            handler = _HANDLER_REGISTRY.get(task.type)
            if handler is None:
                repo.update_status(task.id, "failed", error=f"No handler for type {task.type!r}")
                continue

            start = time.monotonic()
            try:
                handler.run(task)
                duration_ms = (time.monotonic() - start) * 1000
                repo.update_status(task.id, "completed")
                logger.info("Task %d completed in %.0f ms", task.id, duration_ms)
            except Exception as exc:
                error_msg = str(exc)
                if task.retry_count < task.max_retries:
                    repo.update_status(task.id, "retrying", error=error_msg, increment_retry=True)
                else:
                    repo.update_status(task.id, "failed", error=error_msg)
                logger.warning("Task %d failed: %s", task.id, error_msg)
    except Exception as exc:
        logger.error("Inline worker error: %s", exc)
    finally:
        session.close()


def _run_worker() -> None:
    """Run Redis BRPOP worker loop in a background daemon thread."""
    try:
        from worker.main import run
        run(_worker_stop)
    except Exception as exc:
        logger.error("Worker thread crashed: %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()

    event_manager = EventManager()
    LogListener(event_manager)
    set_event_manager(event_manager)

    scheduler = BackgroundScheduler()
    scheduler.add_job(_purge_old_tasks, "interval", hours=1)
    # Inline worker: process pending tasks every 3 s (fallback when Redis unavailable)
    scheduler.add_job(_process_pending_tasks, "interval", seconds=3)
    scheduler.start()

    # Also start the Redis BRPOP worker as a daemon thread
    _worker_stop.clear()
    worker_thread = threading.Thread(target=_run_worker, daemon=True, name="worker")
    worker_thread.start()
    logger.info("task-queue started")

    yield

    _worker_stop.set()
    worker_thread.join(timeout=10)
    scheduler.shutdown(wait=False)
    logger.info("task-queue shutting down")


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
