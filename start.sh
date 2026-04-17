#!/bin/sh
# Start worker in background, then API in foreground.

APP_PORT="${PORT:-8004}"
echo "[start.sh] PORT=${APP_PORT}"
echo "[start.sh] DATABASE_URL=${DATABASE_URL}"
echo "[start.sh] REDIS_URL=${REDIS_URL:+[SET]}"

echo "[start.sh] Starting worker..."
python -m worker.main &

echo "[start.sh] Starting API on port ${APP_PORT}..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT}"
