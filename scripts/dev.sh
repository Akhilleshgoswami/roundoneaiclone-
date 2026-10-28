#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Postgres"
docker compose up -d

echo "==> Stopping old servers"
pkill -f 'uvicorn voiceai.main:app' 2>/dev/null || true
pkill -f 'vite --host 127.0.0.1 --port 5173' 2>/dev/null || true
# also kill mistaken `uvicorn main:app` launches
pkill -f 'uvicorn main:app' 2>/dev/null || true
sleep 1

echo "==> API on :8000"
# Always use this project's uv env + package (src/voiceai)
nohup "$ROOT/.venv/bin/uvicorn" voiceai.main:app \
  --host 127.0.0.1 --port 8000 \
  >> /tmp/voiceai-api.log 2>&1 &
echo $! > /tmp/voiceai-api.pid

echo "==> Frontend on :5173"
nohup npm --prefix "$ROOT/frontend" run dev -- --host 127.0.0.1 --port 5173 \
  >> /tmp/voiceai-fe.log 2>&1 &
echo $! > /tmp/voiceai-fe.pid

sleep 2

if curl -sf http://127.0.0.1:8000/health >/dev/null; then
  echo "API       OK  http://127.0.0.1:8000/docs"
else
  echo "API       FAIL — see /tmp/voiceai-api.log"
  tail -30 /tmp/voiceai-api.log || true
  exit 1
fi

if curl -sf -o /dev/null http://127.0.0.1:5173/; then
  echo "Frontend  OK  http://127.0.0.1:5173"
else
  echo "Frontend  FAIL — see /tmp/voiceai-fe.log"
  tail -30 /tmp/voiceai-fe.log || true
fi
