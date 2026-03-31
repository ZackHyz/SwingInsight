# SwingInsight

SwingInsight is an A-share swing research workspace for turning-point detection, news alignment, feature extraction, and current-state assessment.

## Workspace Layout

- `apps/api`: FastAPI-oriented backend workspace
- `apps/web`: Next.js-oriented frontend workspace
- `infra`: local infrastructure manifests
- `docs`: architecture notes, plans, and runbooks

## Local Setup

### Backend

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

- `TUSHARE_TOKEN`: required for Tushare requests
- `DATA_SOURCE_PRIORITY_DAILY_PRICE`: source priority for daily prices
- `DATA_SOURCE_PRIORITY_NEWS`: source priority for news ingestion
- `DATA_SOURCE_PRIORITY_METADATA`: source priority for stock metadata

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
