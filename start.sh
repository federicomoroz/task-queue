#!/bin/sh
# Start worker in background, then API in foreground.
# If either process dies, the container restarts (Railway policy: on_failure).
set -e

echo "[start.sh] Starting worker..."
python -m worker.main &
WORKER_PID=$!

echo "[start.sh] Starting API on port ${PORT:-8004}..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8004}"
