#!/bin/zsh
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DEMO_DATABASE_URL="${DATABASE_URL:-sqlite+pysqlite:////tmp/swinginsight-live.db}"
LIVE_STOCK_CODE="${LIVE_STOCK_CODE:-600157}"
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
echo "API:  http://127.0.0.1:8000/stocks/${LIVE_STOCK_CODE}"
echo "Web:  http://127.0.0.1:4173/stocks/${LIVE_STOCK_CODE}"
echo "DB:   ${DEMO_DATABASE_URL}"

cd "$ROOT_DIR"
START_DATE="${LIVE_START_DATE:-2024-09-01}"
END_DATE="$(
  ./.venv/bin/python -c 'from datetime import date; print(date.today().isoformat())'
)"

DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -m swinginsight.jobs.cli import-daily-prices --stock-code "$LIVE_STOCK_CODE" --start "$START_DATE" --end "$END_DATE"
DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -m swinginsight.jobs.cli rebuild-segments --stock-code "$LIVE_STOCK_CODE"
DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -m swinginsight.jobs.cli materialize-features --stock-code "$LIVE_STOCK_CODE"

PREDICT_DATE="$(
  DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -c 'from sqlalchemy import func, select; from swinginsight.db.session import session_scope; from swinginsight.db.models.market_data import DailyPrice; import sys; stock_code=sys.argv[1]; ctx = session_scope(); session = ctx.__enter__(); latest = session.scalar(select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_code == stock_code)); ctx.__exit__(None, None, None); print(latest.isoformat() if latest else "")' "$LIVE_STOCK_CODE"
)"
if [[ -z "$PREDICT_DATE" ]]; then
  echo "No imported price rows found for ${LIVE_STOCK_CODE}" >&2
  exit 1
fi

DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -m swinginsight.jobs.cli predict-state --stock-code "$LIVE_STOCK_CODE" --predict-date "$PREDICT_DATE"
DATABASE_URL="$DEMO_DATABASE_URL" PYTHONPATH=apps/api/src ./.venv/bin/python -m uvicorn swinginsight.api.main:create_app --factory --host 127.0.0.1 --port 8000 &
API_PID=$!

cd "$ROOT_DIR/apps/web"
VITE_API_BASE=/api pnpm dev --host 127.0.0.1 --port 4173 &
WEB_PID=$!

wait "$API_PID" "$WEB_PID"
