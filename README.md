# task-queue

A distributed task processing system built with FastAPI and Redis. Client code POSTs a task to the API; the API validates it, writes it to SQLite, and pushes its ID onto a Redis list. One or more worker processes — running in separate Docker containers — compete for tasks via `BRPOP`, execute them, and write the final status back to the database. Workers are horizontally scalable with a single flag.

The project is designed to be read as a portfolio piece: every architectural decision is intentional, every pattern is named, and the entire system can be explored live through the browser UI without touching the terminal.

---

## Live Demo

```bash
git clone https://github.com/federicomoroz/task-queue
cd task-queue
docker compose up --build
```

Open **http://localhost:8004** in your browser.

The **ENQUEUE** tab has four pre-built demo scenarios:

| Scenario | Tasks | What to watch |
|----------|-------|---------------|
| **Echo Burst** | 5 × `echo` → default | All 5 appear as `pending`, flip to `processing` one by one, then `completed` |
| **HTTP Request** | 1 × `http_request` → high | Worker makes a real GET to httpbin.org/uuid — open worker logs to see the response |
| **Multi-Queue Load** | 2 high + 2 default + 2 low | Queue bars on the Dashboard animate as each list drains |
| **Stress Test** | 12 tasks (echo + http) | Shows concurrent processing when running multiple workers |

Click a scenario, switch to the **DASHBOARD** tab, and watch the stats and queue bars update in real time (auto-refresh every 2 seconds).

**Scale to 3 workers:**
```bash
docker compose up --scale worker=3
```

The three workers compete for the same queues. Tasks are distributed naturally — whichever worker wins `BRPOP` first processes the task.

---

## What Problem It Solves

Synchronous APIs have a ceiling: every request must complete before the response is returned. When a task takes time — sending an email, calling a slow third-party API, generating a report — the client blocks, timeouts multiply, and the service becomes fragile under load.

A task queue decouples acceptance from execution:

```
Without a queue                         With a queue
─────────────────────────────────────   ─────────────────────────────────────────────
Client  →  API  →  slow work           Client  →  API  →  (task accepted, 202)
           │                                       │
           └── client blocks 10s                   └── returns immediately

                                        Worker  →  slow work (in background)
                                                →  status updated in DB
                                                →  client polls GET /tasks/{id}
```

`task-queue` demonstrates:

- **Decoupled producer/consumer** — the API and worker are separate processes with no shared memory
- **Reliable delivery** — task IDs are persisted in SQLite before being pushed to Redis; a crashed worker does not lose the record
- **Configurable retry** — transient failures retry up to `max_retries` times before the task is marked `failed`
- **Horizontal scaling** — adding workers requires zero code changes; just `--scale worker=N`
- **Observability** — every status transition is recorded with a timestamp and optional error message

---

## Container Architecture

Three services, each with a single responsibility:

```
┌─────────────────────────────────────────────────────────────────────┐
│                         docker-compose.yml                           │
│                                                                       │
│   ┌─────────────────┐      ┌──────────────────┐                     │
│   │      redis       │      │       api         │  port 8004         │
│   │  Redis 7 Alpine  │◄─────│  FastAPI + uvicorn│◄──── HTTP clients  │
│   │                  │      │                   │                     │
│   │  tq:queue:high   │      │  POST /tasks      │                     │
│   │  tq:queue:default│      │  GET  /tasks      │                     │
│   │  tq:queue:low    │      │  GET  /tasks/{id} │                     │
│   │                  │      │  GET  /queues     │                     │
│   │  volume:         │      │  GET  /health     │                     │
│   │  redis_data:/data│      │  GET  /           │                     │
│   └────────┬─────────┘      └────────┬──────────┘                   │
│            │                         │                               │
│            │  LPUSH task_id          │  SQLite read/write            │
│            │                         │  volume: db_data:/data        │
│            │  BRPOP (blocking)       │                               │
│            │                         │                               │
│   ┌────────▼─────────────────────────▼──────────┐                   │
│   │                   worker (×N)                │                   │
│   │         python -m worker.main                │                   │
│   │                                              │                   │
│   │  BRPOP → load Task from DB → run handler     │                   │
│   │       → update status → emit event           │                   │
│   │                                              │                   │
│   │  volume: db_data:/data  (shared with api)    │                   │
│   └──────────────────────────────────────────────┘                   │
│                                                                       │
│   volumes: redis_data (Redis AOF), db_data (SQLite file)             │
└─────────────────────────────────────────────────────────────────────┘
```

Both `api` and `worker` mount the same `db_data` volume, so they share the SQLite file directly. The API creates the task record; the worker updates it. No ORM-level coordination is needed because each write targets a different column at a different lifecycle stage.

---

## Full Request Lifecycle

### Enqueue path (API)

```
POST /tasks  {"type": "echo", "queue": "default", "payload": {"msg": "hi"}}
  │
  ▼
TasksController.create_task()
  │  injects: Session (SQLite), RedisQueueService, EventManager
  │
  ▼
TaskPipeline.run(type, queue, payload, max_retries)
  │
  ├─► ValidateStep.process(type)
  │     checks type ∈ {"echo", "http_request"}
  │     raises ValueError → HTTP 422 if unknown
  │
  └─► EnqueueStep.process(type, queue, payload, max_retries)
        │
        ├── TaskRepository.create()       → INSERT INTO tasks (status="pending")
        │                                    returns Task with id=42
        │
        ├── RedisQueueService.push()      → LPUSH tq:queue:default "42"
        │
        └── EventManager.emit(TASK_ENQUEUED, task_id=42, queue="default", type="echo")
              │
              └── LogListener._on_enqueued()  → INFO log

  Response: 202 {"id": 42, "status": "pending", ...}
```

### Consume path (Worker)

```
Worker loop (runs forever, one iteration shown)
  │
  ▼
RedisQueueService.pop(["default","high","low"], timeout=5)
  │  → BRPOP tq:queue:high tq:queue:default tq:queue:low 5
  │  → blocks up to 5s, returns ("default", 42)
  │
  ▼
TaskRepository.get(42)       → SELECT * FROM tasks WHERE id=42
  │
  ▼
TaskRepository.update_status(42, "processing")
  │
  ▼
HandlerRegistry["echo"].run(task)
  │
  ├── SUCCESS ─────────────────────────────────────────────────────────────┐
  │   TaskRepository.update_status(42, "completed")                        │
  │   EventManager.emit(TASK_COMPLETED, task_id=42, duration_ms=1043)      │
  │     └── LogListener._on_completed() → INFO log + DB update             │
  │                                                                         │
  └── FAILURE ─────────────────────────────────────────────────────────────┤
      retry_count (0) < max_retries (3)?                                    │
      │                                                                     │
      ├── YES → TaskRepository.update_status(42, "retrying", retry_count++) │
      │         RedisQueueService.push("default", 42)   ← re-enqueue       │
      │         EventManager.emit(TASK_FAILED, final=False)                 │
      │         → task goes back to queue, processed again                  │
      │                                                                     │
      └── NO  → TaskRepository.update_status(42, "failed", error=msg)      │
                EventManager.emit(TASK_FAILED, final=True)                  │
                → terminal state, error saved                               │
                                                                            ▼
                                                              back to BRPOP ←
```

### Task status machine

```
                    ┌─────────┐
     POST /tasks ──►│ pending │
                    └────┬────┘
                         │ worker picks up
                    ┌────▼──────┐
                    │ processing│
                    └────┬──────┘
           success  │         │  failure
          ┌─────────▼──┐   ┌──▼──────────┐
          │ completed   │   │   retrying  │──► re-enqueued
          └─────────────┘   └──────┬──────┘
                                   │ retry_count >= max_retries
                              ┌────▼────┐
                              │ failed  │
                              └─────────┘
```

---

## Directory Structure

```
task-queue/
│
├── app/                             # API process
│   ├── main.py                      # Composition root — wires all deps, lifespan, scheduler
│   │
│   ├── core/
│   │   ├── config.py                # Env vars via pydantic-settings
│   │   ├── database.py              # SQLAlchemy engine, SessionLocal, Base, create_tables()
│   │   ├── event_manager.py         # Synchronous pub/sub bus (subscribe / emit)
│   │   ├── events.py                # Event name constants
│   │   └── redis_client.py          # get_redis() — lazy singleton, module-import pattern
│   │
│   ├── controllers/
│   │   ├── pipeline.py              # TaskPipeline, ValidateStep, EnqueueStep
│   │   ├── tasks_controller.py      # POST /tasks, GET /tasks, GET /tasks/{id}
│   │   └── queues_controller.py     # GET /queues — returns name + LLEN for each queue
│   │
│   ├── models/
│   │   ├── orm.py                   # Task SQLAlchemy model (all fields)
│   │   ├── repositories/
│   │   │   └── task_repository.py   # get, create, update_status, list_tasks, delete_old_completed
│   │   └── services/
│   │       ├── interfaces.py        # TaskHandlerBase ABC, QueueServiceBase ABC
│   │       ├── queue_service.py     # RedisQueueService — LPUSH / BRPOP / LLEN
│   │       ├── log_listener.py      # Subscribes to all 3 events, writes logs + updates DB
│   │       └── handlers/
│   │           ├── echo_handler.py  # Logs message, sleeps 1s
│   │           └── http_handler.py  # Makes HTTP request via httpx.Client
│   │
│   └── views/
│       ├── schemas/
│       │   └── task_schema.py       # TaskIn, TaskOut, QueueOut (Pydantic v2)
│       └── templates/
│           └── spa.py               # Full browser SPA — 4 tabs, no build step
│
├── worker/
│   └── main.py                      # BRPOP loop, handler registry, retry logic
│
├── tests/
│   ├── conftest.py                  # db_engine (StaticPool), fake_redis, test_client fixtures
│   ├── test_event_manager.py
│   ├── test_pipeline.py
│   ├── test_queue_service.py
│   ├── test_task_repository.py
│   ├── test_tasks_api.py
│   └── test_worker.py
│
├── Dockerfile                       # Multi-stage: builder → runtime (API, includes curl)
├── Dockerfile.worker                # Multi-stage: builder → runtime (Worker)
├── docker-compose.yml               # redis + api + worker, named volumes, health checks
├── pytest.ini                       # asyncio_mode = auto
└── requirements.txt
```

---

## Design Patterns

### Pipeline

The API side uses a two-step pipeline. Each step has one responsibility; adding a new step (e.g. deduplication, priority override) means writing one class and inserting it into the pipeline at the composition root — no existing steps change.

```
TaskPipeline
  ├── ValidateStep   — rejects unknown task types before any I/O
  └── EnqueueStep    — creates DB record, pushes to Redis, emits event
```

`ValidateStep` runs first so that if the type is invalid, nothing is written to SQLite or Redis. The error surfaces immediately as an HTTP 422 before any side effects occur.

### Strategy — Handler Registry

The worker uses a plain dictionary as a handler registry. Each value is an instance of `TaskHandlerBase`. Adding a new task type means writing one class and adding one line to the registry — the worker loop, retry logic, and event emission are untouched.

```python
HANDLER_REGISTRY: dict[str, TaskHandlerBase] = {
    "echo":         EchoHandler(),
    "http_request": HttpHandler(http_client),
}
```

```
TaskHandlerBase (ABC)
  ├── EchoHandler       — logs payload["msg"], sleeps 1s
  └── HttpHandler       — makes HTTP request (method, url, optional body)
                          raises on non-2xx → triggers retry path
```

`ValidateStep` in the API is seeded with the same set of known types, so invalid types are rejected before they ever reach the worker.

### EventManager — Pub/Sub Bus

A minimal synchronous bus. The worker and the API each emit domain events; `LogListener` subscribes at startup and reacts to all three. No component imports another's concrete class — they communicate through the bus alone.

```
emitters                  EventManager              subscribers
────────────────          ────────────────          ─────────────────────
EnqueueStep  ──emit()──►  TASK_ENQUEUED   ──────►  LogListener._on_enqueued()
Worker       ──emit()──►  TASK_COMPLETED  ──────►  LogListener._on_completed()
Worker       ──emit()──►  TASK_FAILED     ──────►  LogListener._on_failed()
```

Adding an alerting subscriber (e.g. "page on-call when a task fails with final=True") means creating one new class and subscribing it at startup — the worker code does not change.

### Repository

All database access goes through `TaskRepository`. No controller or service writes raw SQLAlchemy queries inline.

```python
class TaskRepository:
    def get(self, task_id: int) -> Task | None
    def create(self, *, type, queue, payload, max_retries) -> Task
    def update_status(self, task_id, status, *, error, increment_retry) -> Task | None
    def list_tasks(self, queue, status, limit) -> list[Task]
    def delete_old_completed(self, before: datetime) -> int
```

### Composition Root

`app/main.py` is the only place where concrete dependencies are created. Everything else receives what it needs through constructor injection or FastAPI's `Depends`. The entire wiring can be replaced for testing by patching two module-level variables (`_db_mod.SessionLocal`, `_redis_mod.get_redis`).

```python
# app/main.py — lifespan()
create_tables()
event_manager = EventManager()
LogListener(event_manager)          # subscriber wired here
set_event_manager(event_manager)    # injected into controller
scheduler.add_job(_purge_old_tasks, "interval", hours=1)
```

---

## SOLID Application

| Principle | Implementation |
|-----------|----------------|
| **S** — Single Responsibility | `ValidateStep` only validates. `EnqueueStep` only persists + pushes. `EchoHandler` only runs echo logic. `LogListener` only writes logs. No class has two reasons to change. |
| **O** — Open/Closed | New task type: add one handler class + one registry entry. New pipeline step: add one class + insert at composition root. New event side-effect: add one subscriber. No existing code is modified in any of these cases. |
| **L** — Liskov Substitution | Any `TaskHandlerBase` subclass substitutes in the registry. `FakeRedis` substitutes for `redis.Redis` in tests — all `RedisQueueService` calls pass unchanged. |
| **I** — Interface Segregation | `QueueServiceBase` exposes only `push`, `pop`, `depth`. `TaskHandlerBase` exposes only `run`. No fat interfaces that force implementors to define methods they don't need. |
| **D** — Dependency Inversion | `TaskPipeline` receives `repo`, `queue_service`, and `event_manager` by injection — it never instantiates them. `Worker` receives the same. `LogListener` receives `EventManager` by constructor — it does not import the worker or the API. |

---

## Redis Key Schema

```
tq:queue:default    Redis List — LPUSH on enqueue, BRPOP on consume
tq:queue:high       Redis List — same
tq:queue:low        Redis List — same
```

`LPUSH` pushes to the left (head); `BRPOP` pops from the right (tail). This gives **FIFO** order within each queue.

Worker processes pop from `["default", "high", "low"]` in that order — Redis checks lists left to right, so the first non-empty list wins. To implement priority, route important tasks to `high` and they will be picked up before `default` tasks.

---

## Horizontal Scaling

```
                          redis
                         ┌─────┐
                         │     │  tq:queue:high    [ 42, 43, 44 ]
  POST /tasks ──────────►│     │  tq:queue:default [ 45, 46 ]
                         │     │  tq:queue:low     [ 47 ]
                         └──┬──┘
                            │  BRPOP (each worker blocks independently)
              ┌─────────────┼─────────────┐
              │             │             │
         ┌────▼────┐   ┌────▼────┐   ┌────▼────┐
         │ worker1 │   │ worker2 │   │ worker3 │
         │  id=42  │   │  id=43  │   │  id=44  │
         └─────────┘   └─────────┘   └─────────┘
              │             │             │
              └─────────────▼─────────────┘
                        db_data volume
                       (shared SQLite)
```

Each worker runs `BRPOP` on the same list. Redis delivers each task ID to exactly one worker — there is no double-processing. Workers write to SQLite independently; SQLite's WAL mode handles concurrent writes from multiple processes.

---

## Data Model

```
tasks
─────────────────────────────────────────────────────────────────────
id           INTEGER  PRIMARY KEY AUTOINCREMENT
type         TEXT     "echo" | "http_request"
queue        TEXT     "default" | "high" | "low" (or any custom value)
payload      TEXT     JSON string  e.g. {"msg": "hello"}
status       TEXT     "pending" | "processing" | "completed" | "failed" | "retrying"
max_retries  INTEGER  default 3  (0–10, set at enqueue time)
retry_count  INTEGER  default 0  (incremented on each retry)
error        TEXT     nullable — last error message (set on failure)
created_at   DATETIME server default NOW
updated_at   DATETIME server default NOW, updated on every status change
```

---

## Browser UI

`GET /` serves a single-page app with four tabs. No build step, no framework — vanilla JS talking to the REST API.

| Tab | What you can do |
|-----|-----------------|
| **DASHBOARD** | Stats (total, pending, processing, completed, failed, retrying, success rate), animated queue depth bars, recent activity table. Auto-refreshes every 2 seconds. |
| **ENQUEUE** | Four quick-scenario buttons for live demos. Below them: a manual form for custom task submission. An enqueue log shows each submitted task as it's accepted. |
| **TASKS** | Full task list, filterable by queue and status. Shows ID, type, queue, status badge, retry counter, timestamps, and error message. |
| **QUEUES** | Visual depth bars for each queue, Redis key for each, plus a reference section on the key schema and scaling commands. |

---

## API Reference

### Tasks

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `POST` | `/tasks` | 202 | Create and enqueue task |
| `GET` | `/tasks` | 200 | List tasks (filters: `queue`, `status`; `limit` 1–500) |
| `GET` | `/tasks/{id}` | 200 / 404 | Single task detail |

**POST /tasks body:**
```json
{
  "type":        "echo | http_request",
  "queue":       "default | high | low",
  "payload":     {},
  "max_retries": 3
}
```

**Payload by type:**

| type | payload keys | notes |
|------|-------------|-------|
| `echo` | `msg` (string) | Worker logs the message and sleeps 1 second |
| `http_request` | `method` (GET/POST/…), `url` (string), `body` (object, optional) | Worker calls the URL and raises on non-2xx |

### Queues

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/queues` | 200 | List configured queues with current depth |

**Response:**
```json
[
  {"name": "default", "depth": 3},
  {"name": "high",    "depth": 0},
  {"name": "low",     "depth": 1}
]
```

### Health

| Method | Path | Status | Description |
|--------|------|--------|-------------|
| `GET` | `/health` | 200 | Liveness check — used by Docker health check |

**Response:** `{"status": "ok"}`

### UI

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Browser SPA — Dashboard, Enqueue, Tasks, Queues |
| `GET` | `/docs` | Swagger UI |

---

## Configuration

All values are read from environment variables (or a `.env` file).

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `DATABASE_URL` | `sqlite:////data/tasks.db` | SQLAlchemy database URL |
| `WORKER_QUEUES` | `default,high,low` | Comma-separated list of queues workers listen on |
| `BRPOP_TIMEOUT` | `5` | Seconds a worker blocks waiting for a task |
| `PURGE_COMPLETED_AFTER_HOURS` | `24` | Completed tasks older than this are deleted by the background scheduler |

In `docker-compose.yml` these are injected directly into each service's `environment` block.

---

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

37 tests across 6 modules, all passing in under 1.5 seconds:

| Module | Tests | What's covered |
|--------|-------|----------------|
| `test_event_manager` | 4 | Subscribe/emit, multiple listeners, event isolation |
| `test_pipeline` | 5 | ValidateStep rejects unknowns, EnqueueStep persists + pushes, event emission |
| `test_queue_service` | 6 | LPUSH/BRPOP mechanics, FIFO order, key schema, empty-queue return |
| `test_task_repository` | 8 | CRUD, status transitions, retry counter, filtering, purge |
| `test_tasks_api` | 10 | POST/GET endpoints, unknown type rejection, 404 path, filters, health, SPA |
| `test_worker` | 4 | Successful run, retry-on-failure, final failure, unknown handler |

**Key test infrastructure decisions:**
- `fakeredis.FakeRedis` replaces Redis — `RedisQueueService` works without a running server
- `sqlalchemy.pool.StaticPool` on the in-memory SQLite engine — all sessions share the same connection, so tables created in the fixture are visible inside the app
- Module-level imports (`import app.core.database as _db_mod`) instead of `from ... import SessionLocal` — allows the test fixture to patch the reference and have it propagate to all callers

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API framework | FastAPI 0.115 + uvicorn 0.32 |
| Language | Python 3.12 |
| Message broker | Redis 7 Alpine (LPUSH / BRPOP) |
| Database | SQLite 3 + SQLAlchemy 2.0 (mapped columns) |
| HTTP client | httpx 0.27 (sync, used in HttpHandler and tests) |
| Scheduler | APScheduler 3.10 (background purge job) |
| Validation | Pydantic v2 + pydantic-settings |
| Testing | pytest 8 + pytest-asyncio + fakeredis |
| Containers | Docker (Python 3.12-slim, multi-stage build) |
| Orchestration | Docker Compose v2 |
