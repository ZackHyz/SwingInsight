# Dev Setup

## Prerequisites

- Python 3.12+ available as `python3`
- Node.js and `pnpm`

## Backend

```bash
python3 -m venv .venv
.venv/bin/pip install -e apps/api pytest
```

The backend install pulls the live market-data adapters, including `tushare` and `mootdx`.

Set `TUSHARE_TOKEN` when you want Tushare fallback to succeed for daily prices or stock metadata. The default runtime order is:

- daily prices: `akshare,tushare,mootdx`
- stock metadata: `akshare,tushare,mootdx` with `mootdx` skipped because it does not implement metadata

Run the full backend suite:

```bash
cd apps/api
../../.venv/bin/pytest -v
```

## Frontend

Install frontend dependencies and run unit tests:

```bash
cd apps/web
pnpm install
pnpm test -- --run
pnpm typecheck
```

Install Playwright browsers when you need browser smoke coverage:

```bash
cd apps/web
pnpm exec playwright install chromium
pnpm test:e2e
```

## Demo Database

The demo seed script defaults to a local SQLite file:

```bash
.venv/bin/python apps/api/scripts/seed_demo_data.py
```

Override the target database when needed:

```bash
DATABASE_URL=postgresql+psycopg://swinginsight:swinginsight@127.0.0.1:5432/swinginsight \
  .venv/bin/python apps/api/scripts/seed_demo_data.py
```
