# Research Refresh Decoupling And Horizon Contracts Design

## 1. Scope

This design covers a single implementation round for the following P0 items:

1. Decouple `GET /stocks/{code}` from refresh/materialization.
2. Add task-level observability for refresh stages.
3. Refactor `api/routes/stocks.py` by separating read/assemble/route concerns.
4. Replace prediction-path silent fallback with structured error reporting.
5. Formalize and test 5d/10d/20d contracts across API, jobs, and UI.

Out of scope:

- Introducing Celery/Redis or external queue middleware.
- Major UI redesign beyond status and freshness display.
- Changes to pattern ranking algorithm itself.

## 2. Current Pain Points

- `GET /stocks/{stock_code}` currently invokes `StockResearchService.ensure_stock_ready()`, mixing read path with long-running refresh pipeline.
- `task_run_log` exists but stage-level observability is fragmented and not stitched with a single refresh task identity.
- `apps/api/src/swinginsight/api/routes/stocks.py` holds heavy payload assembly and business aggregation logic.
- `PredictionService` has broad silent fallback (`except Exception`) that hides root causes.
- 5/10/20 horizon semantics are exposed in multiple places without one explicit contract.

## 3. Target Architecture

### 3.1 Read vs Refresh Split

- `GET /stocks/{code}`: read-only; no refresh side effects.
- `POST /stocks/{code}/refresh`: enqueue-or-reuse refresh task and return task metadata.
- `GET /stocks/{code}/refresh-status`: return latest task state for polling and UI display.

### 3.2 Task Model and Idempotency

Introduce a first-class refresh task entity (DB-backed):

- `task_id`, `stock_code`, `status`, `created_at`, `started_at`, `ended_at`.
- Status enum: `queued`, `running`, `success`, `failed`, `partial`.
- Idempotency rule: for same `stock_code`, if latest task is `queued/running`, return existing `task_id` instead of creating a new one.

### 3.3 Refresh Stage Observability

Each stage writes structured execution rows linked to one `task_id`:

1. `price_import`
2. `news_import`
3. `news_process`
4. `news_align`
5. `pattern_materialize`
6. `prediction`

Each stage records:

- `status`
- `source`
- `rows_changed`
- `duration_ms`
- `error_message`

### 3.4 Stocks Route Refactor

Split responsibilities:

- `readers/`: DB reads only.
- `assemblers/`: payload composition and field normalization.
- `routes/`: HTTP semantics, status code mapping, and dependency wiring.

`routes/stocks.py` should not contain large aggregation or formatting internals after refactor.

### 3.5 Prediction Fallback Semantics

Replace silent fallback with explicit structured fields:

- `fallback_used: bool`
- `fallback_reason: str | null`
- `fallback_error_type: str | null`
- `fallback_stage: str | null`

Rules:

- Expected degradations (e.g., insufficient artifacts) map to controlled fallback reasons.
- Unexpected exceptions are logged with structured metadata and surfaced through fallback fields.
- Development environment prints full traceback.

### 3.6 Horizon Contract (5d/10d/20d)

Formalize endpoint behavior:

- `/pattern-score`: calibrated rates and horizon metadata remain consistent with 5/10/20 semantics.
- `/similar-cases`: expose `future_return_5d`, `future_return_10d`, `future_return_20d`.
- `/group-stat`:
  - `horizon_days = [5, 10, 20]`
  - `return_distributions["5"|"10"|"20"]`
  - keep backward compatibility field `return_distribution` as 10d alias.

Missing-data semantics:

- No sample: empty arrays and `sample_count = 0`.
- Insufficient sample: computed values allowed, but explicitly marked with low confidence and insufficient-sample flag where applicable.

## 4. API Additions

### 4.1 `POST /stocks/{stock_code}/refresh`

Response:

- `task_id`
- `stock_code`
- `status` (`queued` or existing `running`)
- `created_at`
- `reused` (true when returning existing queued/running task)

### 4.2 `GET /stocks/{stock_code}/refresh-status`

Response:

- top-level task metadata (status, timestamps, error summary).
- ordered stage details with per-stage metrics.
- optional freshness summary (`latest_success_at`, `last_data_trade_date`, `data_source_summary`).

## 5. Testing Strategy

1. API contract tests:
   - read endpoint no longer triggers refresh.
   - refresh enqueue/idempotent reuse behavior.
   - refresh status payload completeness.
2. Service tests:
   - stage state transitions and partial/failure handling.
   - structured fallback fields in prediction output.
3. Horizon contract tests:
   - `/pattern-score`, `/similar-cases`, `/group-stat` consistency for 5/10/20.
   - missing/insufficient sample semantics.
4. Frontend tests:
   - status indicator rendering and polling behavior.
   - 5/10/20 tabs handle empty/missing distributions safely.

## 6. Rollout Plan

1. Add new refresh task schema and service scaffolding.
2. Introduce new refresh APIs and poll-ready status model.
3. Remove implicit refresh call from `GET /stocks/{code}`.
4. Refactor stocks route into reader/assembler layers.
5. Land structured fallback reporting.
6. Land horizon contract and tests.
7. Update README/runbook with operational commands and troubleshooting flow.

## 7. Risks and Mitigations

- Risk: duplicate execution under multi-worker race.
  - Mitigation: transactional idempotency check + row lock on latest in-flight task.
- Risk: partial refresh leaves mixed data freshness.
  - Mitigation: stage-level status plus UI display of last successful refresh timestamp.
- Risk: backward compatibility break for existing consumers.
  - Mitigation: preserve existing fields and add new fields additively.
