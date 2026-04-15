# Repository Guidelines

## Project Structure & Module Organization
`SwingInsight` is split into two apps:
- `apps/api`: FastAPI backend (`src/swinginsight`), Alembic migrations (`alembic`), and pytest suites (`tests`).
- `apps/web`: Vite + React frontend (`src`), with Vitest tests in `tests`.

Supporting directories:
- `docs/`: runbooks, ADRs, and planning/design docs.
- `scripts/run_demo.sh`: one-command local demo bootstrap.
- `infra/`: local infrastructure definitions (e.g., Docker compose for PostgreSQL).

## Build, Test, and Development Commands
- `make api-venv`: create `.venv` and install backend dependencies.
- `make api-test`: run backend tests (`apps/api`).
- `make web-install`: install frontend dependencies.
- `make web-test`: run frontend tests.
- `make demo`: seed/refresh demo data and start API + web together.

Direct commands commonly used:
- Backend tests: `cd apps/api && ../../.venv/bin/pytest -v`
- Frontend tests: `cd apps/web && pnpm test -- --run`
- Frontend dev server: `cd apps/web && pnpm dev`

## Coding Style & Naming Conventions
- Python: PEP 8, 4-space indentation, type hints preferred, snake_case for functions/files.
- TypeScript/React: 2-space indentation, PascalCase for components, camelCase for variables/hooks (`useXxx`).
- Keep modules focused; place API route composition in `api/routes`, domain logic in `services`/`domain`.
- Follow existing naming patterns for payload fields (snake_case from backend, typed in frontend API client).

## Testing Guidelines
- Backend uses `pytest`; frontend uses `vitest` + Testing Library.
- Add tests for new behavior and regressions in the nearest existing suite.
- Test filenames should mirror scope, e.g. `test_pattern_insight_api.py`, `prediction-panel.test.tsx`.
- Prefer deterministic, isolated tests (in-memory SQLite for backend API tests when possible).

## Commit & Pull Request Guidelines
- Use conventional-style prefixes seen in history: `feat:`, `fix:`, `test:`, `docs:`.
- Keep commit messages imperative and specific (e.g., `feat: add pattern score endpoints`).
- PRs should include:
  - What changed and why.
  - Test evidence (commands + pass result).
  - UI screenshots/GIFs for frontend-visible changes.
  - Linked issue/task if applicable.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit secrets.
- Key env vars include `TUSHARE_TOKEN` and `DATA_SOURCE_PRIORITY_*`.
- Validate data-source fallbacks locally before merging market-data related changes.
