# task-queue

A task queue system demonstrating Docker multi-container architecture with FastAPI and Redis.

## Tech Stack
- **API**: FastAPI + uvicorn (port 8004)
- **Broker**: Redis 7 (LPUSH/BRPOP)
- **DB**: SQLite + SQLAlchemy 2.0
- **Worker**: Separate Python process, horizontally scalable
- **Patterns**: SOLID + EventManager + Pipeline + Repository + Strategy

## Quick Start

```bash
docker compose up --build
```

API available at `http://localhost:8004`

### Scale workers

```bash
docker compose up --scale worker=3
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /tasks | Create and enqueue a task |
| GET | /tasks | List tasks (filter: queue, status) |
| GET | /tasks/{id} | Task detail |
| GET | /queues | Queue stats (name + depth) |
| GET | /health | Liveness check |
| GET | / | SPA dashboard |

### Create a task

```bash
# Echo task
curl -X POST http://localhost:8004/tasks \
  -H "Content-Type: application/json" \
  -d '{"type":"echo","queue":"default","payload":{"msg":"hello"}}'

# HTTP request task
curl -X POST http://localhost:8004/tasks \
  -H "Content-Type: application/json" \
  -d '{"type":"http_request","queue":"high","payload":{"method":"GET","url":"https://httpbin.org/get"}}'
```

## Task Types

| Type | Payload | Description |
|------|---------|-------------|
| `echo` | `{"msg": "..."}` | Logs message, sleeps 1s (demo) |
| `http_request` | `{"method": "GET/POST", "url": "...", "body": {}}` | Makes HTTP request |

## Task Status Flow

```
pending → processing → completed
                    ↘ retrying → processing (up to max_retries)
                              ↘ failed
```

## Run Tests

```bash
pip install -r requirements.txt
pytest
```

## Architecture

```
EventManager (pub/sub bus)
  ↑ TaskEnqueued, TaskCompleted, TaskFailed

POST /tasks
  └── Pipeline
        ├── ValidateStep  — handler type must exist
        └── EnqueueStep   — DB insert + Redis LPUSH → emits TaskEnqueued

Worker (BRPOP loop)
  ├── HandlerRegistry["echo"]         → EchoHandler
  └── HandlerRegistry["http_request"] → HttpHandler
        → success: emit TaskCompleted
        → error:   retry or emit TaskFailed

LogListener → updates Task.status in DB
```
