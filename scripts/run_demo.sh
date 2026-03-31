#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEMO_DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:////tmp/swinginsight-demo.db}"
API_PID=""
WEB_PID=""

cleanup() {
  if [[ -n "$API_PID" ]]; then
    kill "$API_PID" >/dev/null 2>&1 || true
  fi
  if [[ -n "$WEB_PID" ]]; then
    kill "$WEB_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT INT TERM

echo "Starting SwingInsight demo"
echo "API:  http://127.0.0.1:8000/stocks/000001"
echo "Web:  http://127.0.0.1:4173/stocks/000001"
echo "DB:   ${DEMO_DATABASE_URL}"

cd "$ROOT_DIR"
DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -m uvicorn swinginsight.api.main:create_app --factory --host 127.0.0.1 --port 8000 &
API_PID=$!

cd "$ROOT_DIR/apps/web"
node tests/e2e/server.mjs &
WEB_PID=$!

wait "$API_PID" "$WEB_PID"
