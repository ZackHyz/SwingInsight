# SwingInsight

SwingInsight is an A-share swing research workspace for turning-point detection, news alignment, feature extraction, and current-state assessment.

## Workspace Layout

- `apps/api`: FastAPI-oriented backend workspace
- `apps/web`: Next.js-oriented frontend workspace
- `infra`: local infrastructure manifests
- `docs`: architecture notes, plans, and runbooks

## Local Setup

### Backend

Backend dependencies target Python 3.12+.

```bash
python3 -m venv .venv
.venv/bin/pip install -e apps/api pytest
cd apps/api
../../.venv/bin/pytest -v
```

### Frontend

```bash
cd apps/web
pnpm install
pnpm test -- --run
pnpm typecheck
```

Playwright smoke coverage:

```bash
cd apps/web
pnpm exec playwright install chromium
pnpm test:e2e
```

## Environment Variables

Copy `.env.example` to `.env` and provide real values locally.

- `TUSHARE_TOKEN`: optional while `akshare` succeeds, but required for Tushare daily-price or metadata fallback to work
- `DATA_SOURCE_PRIORITY_DAILY_PRICE`: source priority for daily prices, default `akshare,tushare,mootdx`
- `DATA_SOURCE_PRIORITY_NEWS`: source priority for news ingestion
- `DATA_SOURCE_PRIORITY_METADATA`: source priority for stock metadata, default `akshare,tushare,mootdx`

Daily-price refresh tries providers in order until one succeeds and records the actual winner in `daily_price.data_source` plus `task_run_log`.

Stock metadata uses its own fallback chain instead of borrowing the daily-price provider. `mootdx` remains a daily-price-only fallback and is skipped automatically for metadata lookups.

News source priority currently supports `cninfo`, `eastmoney`, `akshare`, and `demo`. Example:

```bash
export DATA_SOURCE_PRIORITY_NEWS=cninfo,eastmoney,akshare
```

Example market-data overrides:

```bash
export DATA_SOURCE_PRIORITY_DAILY_PRICE=akshare,tushare,mootdx
export DATA_SOURCE_PRIORITY_METADATA=akshare,tushare,mootdx
export TUSHARE_TOKEN=your-real-token
```

## Infrastructure

The repo includes `infra/docker-compose.yml` for a local PostgreSQL service.

```bash
docker compose -f infra/docker-compose.yml up -d
# or, if your setup exposes the standalone binary:
docker-compose -f infra/docker-compose.yml up -d
```

You can validate the compose file with either command:

```bash
docker compose -f infra/docker-compose.yml config
# or
docker-compose -f infra/docker-compose.yml config
```

If Docker is not installed or not on `PATH`, Task 1 smoke tests can still run without the database container.

## Demo Seed And Launch

Seed repeatable demo data into a local SQLite database:

```bash
.venv/bin/python apps/api/scripts/seed_demo_data.py
```

Launch the API plus browser smoke harness:

```bash
make demo
```

The default demo URLs are:

- `http://127.0.0.1:8000/stocks/000001`
- `http://127.0.0.1:4173/stocks/000001`

See `docs/runbooks/dev-setup.md` and `docs/runbooks/demo-flow.md` for the full developer and demo walkthroughs.

## News Pipeline Operations

Incremental news refresh defaults to the most recent 7 calendar days when `--start/--end` are omitted.

```bash
cd apps/api
../../.venv/bin/python -m swinginsight.jobs.cli import-news --stock-code 000001
../../.venv/bin/python -m swinginsight.jobs.cli process-news --stock-code 000001
../../.venv/bin/python -m swinginsight.jobs.cli align-news --stock-code 000001
```

Backfill a bounded window explicitly:

```bash
cd apps/api
../../.venv/bin/python -m swinginsight.jobs.cli import-news --stock-code 000001 --start 2026-03-01 --end 2026-03-31 --source cninfo --source eastmoney
../../.venv/bin/python -m swinginsight.jobs.cli process-news --stock-code 000001 --start 2026-03-01 --end 2026-03-31
../../.venv/bin/python -m swinginsight.jobs.cli align-news --stock-code 000001 --start 2026-03-01 --end 2026-03-31
```

## News Sentiment V1

`process-news` now emits event-level sentiment outputs into `news_sentiment_result` and `news_event_result`.

```bash
cd apps/api
../../.venv/bin/python -m swinginsight.jobs.cli process-news --stock-code 600010 --start 2026-03-19 --end 2026-04-02
```

Example output:

```text
process-news stock_code=600010 processed=17 duplicates=0 sentiment_results=17 event_results=21 conflict_news=1
```

Quick verification queries:

```sql
select count(*) from news_sentiment_result;
select news_id, sentiment_label, sentiment_score_base, sentiment_score_adjusted, event_conflict_flag
from news_sentiment_result
order by id desc
limit 10;

select news_id, event_type, event_polarity, event_strength
from news_event_result
order by id desc
limit 20;
```

Research payloads also expose these V1 fields on `/stocks/{code}` news items:

- `sentiment_score_adjusted`
- `event_types`
- `event_conflict_flag`

Page-driven research requests call the same incremental pipeline automatically for the latest trading-date window, then only rematerialize overlapping segment features instead of rebuilding all historical news mappings.

## Pattern Similarity V1 Operations

Single-stock pattern backfill order:

```bash
cd apps/api
../../.venv/bin/python -m swinginsight.jobs.cli rebuild-segments --stock-code 600010 --algo zigzag
../../.venv/bin/python -m swinginsight.jobs.cli build-pattern-windows --stock-code 600010
../../.venv/bin/python -m swinginsight.jobs.cli materialize-pattern-features --stock-code 600010
../../.venv/bin/python -m swinginsight.jobs.cli materialize-pattern-future-stats --stock-code 600010
```

Expected CLI outputs:

```text
build-pattern-windows stock_code=600010 window_size=7 created=... updated=... skipped=...
materialize-pattern-features stock_code=600010 windows=... features=... skipped=...
materialize-pattern-future-stats stock_code=600010 updated=... skipped=...
```

Quick verification queries:

```sql
select count(*) from pattern_window where stock_code = '600010';
select count(*) from pattern_feature pf join pattern_window pw on pw.id = pf.window_id where pw.stock_code = '600010';
select count(*) from pattern_future_stat pfs join pattern_window pw on pw.id = pfs.window_id where pw.stock_code = '600010';
```

Pattern-driven prediction payloads now expose:

- `query_window`
- `group_stat`
- per-sample `window_start_date` / `window_end_date`
- per-sample `segment_start_date` / `segment_end_date`

## Failure Debugging

Start from `task_run_log` when a news job appears stale or empty:

```sql
select task_type, target_code, status, result_summary, error_message, start_time
from task_run_log
order by start_time desc;
```

Then check the three persistent stages directly:

- `news_raw`: source ingestion and dedupe inputs
- `news_processed`: classification, sentiment, heat, keywords
- `point_news_map` / `segment_news_map`: turning-point and segment alignment outputs
