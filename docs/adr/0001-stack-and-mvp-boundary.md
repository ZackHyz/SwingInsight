# ADR 0001: Stack And MVP Boundary

## Status

Accepted

## Context

SwingInsight starts from an empty repository and needs a practical MVP boundary that favors research correctness over breadth.

## Decision

- Use Python for backend domain logic and API scaffolding.
- Use TypeScript with a Next.js-compatible structure for the frontend.
- Use PostgreSQL as the primary persistence target for local development and future migrations.
- Keep Task 1 limited to repository bootstrap, smoke tests, local config, and documentation.
- Treat `TUSHARE_TOKEN` as a local environment variable only.

## Consequences

- The repository can grow into the planned monorepo layout without rework.
- Task 1 remains lightweight and verifiable even when Docker is unavailable locally.
- Heavier dependencies such as FastAPI, SQLAlchemy, and Next.js runtime setup are deferred to later tasks.
