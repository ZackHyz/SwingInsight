# P0 Refresh Decoupling And Contracts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decouple research read API from refresh pipeline, add refresh observability, formalize 5d/10d/20d contracts, and remove silent prediction fallback.

**Architecture:** Introduce a DB-backed refresh task/state model and explicit refresh APIs while keeping `GET /stocks/{code}` read-only. Split stock payload reads/assembly into dedicated modules, and standardize horizon/fallback semantics as explicit API contracts with tests.

**Tech Stack:** FastAPI, SQLAlchemy ORM + Alembic, pytest, React + Vitest.

---

## File Structure

- Create: `apps/api/src/swinginsight/db/models/refresh.py`
- Modify: `apps/api/src/swinginsight/db/models/__init__.py`
- Create: `apps/api/alembic/versions/0008_refresh_task.py`
- Create: `apps/api/src/swinginsight/services/stock_refresh_service.py`
- Create: `apps/api/src/swinginsight/api/routes/refresh.py`
- Modify: `apps/api/src/swinginsight/api/main.py`
- Create: `apps/api/src/swinginsight/api/readers/stock_research_reader.py`
- Create: `apps/api/src/swinginsight/api/assemblers/stock_research_assembler.py`
- Create: `apps/api/src/swinginsight/api/assemblers/pattern_insight_assembler.py`
- Modify: `apps/api/src/swinginsight/api/routes/stocks.py`
- Modify: `apps/api/src/swinginsight/services/prediction_service.py`
- Modify: `apps/api/src/swinginsight/api/routes/predictions.py`
- Modify: `apps/api/src/swinginsight/services/stock_research_service.py`
- Modify: `apps/web/src/lib/api.ts`
- Modify: `apps/web/src/app/stocks/[stockCode]/page.tsx`
- Create: `apps/web/src/hooks/use-refresh-status.ts`
- Create: `apps/api/tests/api/test_refresh_api.py`
- Create: `apps/api/tests/services/test_stock_refresh_service.py`
- Create: `apps/api/tests/api/test_stock_read_path_no_refresh.py`
- Modify: `apps/api/tests/api/test_pattern_insight_api.py`
- Modify: `apps/api/tests/domain/test_prediction_service.py`
- Create: `apps/web/tests/use-refresh-status.test.tsx`
- Modify: `apps/web/tests/stock-research-page-fetch.test.tsx`
- Modify: `README.md`

### Task 1: Add Refresh Task Schema

**Files:**
- Create: `apps/api/src/swinginsight/db/models/refresh.py`
- Modify: `apps/api/src/swinginsight/db/models/__init__.py`
- Create: `apps/api/alembic/versions/0008_refresh_task.py`
- Create: `apps/api/tests/domain/test_refresh_task_model.py`

- [ ] **Step 1: Write failing model test**

```python
def test_refresh_task_tables_exist(session):
    from sqlalchemy import inspect
    inspector = inspect(session.bind)
    assert "stock_refresh_task" in inspector.get_table_names()
    assert "stock_refresh_stage_log" in inspector.get_table_names()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_refresh_task_model.py`  
Expected: FAIL with missing table/model.

- [ ] **Step 3: Add models and migration**

```python
class StockRefreshTask(CreatedAtMixin, Base):
    __tablename__ = "stock_refresh_task"
    id = mapped_column(BIGINT_TYPE, primary_key=True)
    stock_code = mapped_column(String(16), nullable=False, index=True)
    status = mapped_column(String(16), nullable=False, index=True)  # queued/running/success/failed/partial
    start_time = mapped_column(DateTime(), nullable=True)
    end_time = mapped_column(DateTime(), nullable=True)
    error_message = mapped_column(Text(), nullable=True)
```

- [ ] **Step 4: Re-run test and migration checks**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_refresh_task_model.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/db/models/refresh.py apps/api/src/swinginsight/db/models/__init__.py apps/api/alembic/versions/0008_refresh_task.py apps/api/tests/domain/test_refresh_task_model.py
git commit -m "feat: add stock refresh task schema"
```

### Task 2: Implement Refresh Orchestrator + Stage Observability

**Files:**
- Create: `apps/api/src/swinginsight/services/stock_refresh_service.py`
- Modify: `apps/api/src/swinginsight/services/stock_research_service.py`
- Create: `apps/api/tests/services/test_stock_refresh_service.py`

- [ ] **Step 1: Write failing service tests (idempotency + stage transitions)**

```python
def test_enqueue_refresh_reuses_running_task(session):
    service = StockRefreshService(session)
    first = service.enqueue("600010")
    second = service.enqueue("600010")
    assert first.id == second.id
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_stock_refresh_service.py`  
Expected: FAIL with missing service.

- [ ] **Step 3: Implement orchestration**

```python
class StockRefreshService:
    def enqueue(self, stock_code: str) -> StockRefreshTask: ...
    def run(self, task_id: int) -> StockRefreshTask: ...
    def latest_status(self, stock_code: str) -> dict[str, object] | None: ...
```

Stage executor writes one `stock_refresh_stage_log` row per stage (`price_import`, `news_import`, `news_process`, `news_align`, `pattern_materialize`, `prediction`) with `duration_ms`, `status`, `source`, `rows_changed`, `error_message`.

- [ ] **Step 4: Run service tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_stock_refresh_service.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/services/stock_refresh_service.py apps/api/src/swinginsight/services/stock_research_service.py apps/api/tests/services/test_stock_refresh_service.py
git commit -m "feat: add refresh orchestration and stage observability"
```

### Task 3: Add Refresh APIs and Decouple Read Path

**Files:**
- Create: `apps/api/src/swinginsight/api/routes/refresh.py`
- Modify: `apps/api/src/swinginsight/api/main.py`
- Create: `apps/api/tests/api/test_refresh_api.py`
- Create: `apps/api/tests/api/test_stock_read_path_no_refresh.py`

- [ ] **Step 1: Write failing API tests**

```python
def test_post_refresh_returns_task_id(client):
    resp = client.post("/stocks/600010/refresh")
    assert resp.status_code == 200
    assert "task_id" in resp.json()

def test_get_stock_does_not_call_ensure_stock_ready(monkeypatch, client):
    called = {"value": False}
    monkeypatch.setattr(StockResearchService, "ensure_stock_ready", lambda *_args, **_kwargs: called.__setitem__("value", True))
    client.get("/stocks/600010")
    assert called["value"] is False
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/api/test_refresh_api.py tests/api/test_stock_read_path_no_refresh.py`  
Expected: FAIL with missing endpoints/behavior.

- [ ] **Step 3: Add endpoints and remove auto-refresh from GET**

```python
@app.post("/stocks/{stock_code}/refresh")
def post_stock_refresh(...): ...

@app.get("/stocks/{stock_code}/refresh-status")
def get_stock_refresh_status(...): ...

@app.get("/stocks/{stock_code}")
def get_stock(...):
    payload = get_stock_research_payload(...)
```

- [ ] **Step 4: Re-run API tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/api/test_refresh_api.py tests/api/test_stock_read_path_no_refresh.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/api/routes/refresh.py apps/api/src/swinginsight/api/main.py apps/api/tests/api/test_refresh_api.py apps/api/tests/api/test_stock_read_path_no_refresh.py
git commit -m "feat: decouple stock read endpoint and add refresh apis"
```

### Task 4: Refactor Stocks Route to Reader/Assembler Layers

**Files:**
- Create: `apps/api/src/swinginsight/api/readers/stock_research_reader.py`
- Create: `apps/api/src/swinginsight/api/assemblers/stock_research_assembler.py`
- Create: `apps/api/src/swinginsight/api/assemblers/pattern_insight_assembler.py`
- Modify: `apps/api/src/swinginsight/api/routes/stocks.py`
- Create: `apps/api/tests/api/test_stock_research_assembler.py`

- [ ] **Step 1: Write failing assembler unit test**

```python
def test_assemble_research_payload_handles_empty_news():
    payload = assemble_stock_research_payload(stock=..., prices=[], news_rows=[], prediction=None)
    assert payload["news_items"] == []
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/api/test_stock_research_assembler.py`  
Expected: FAIL with missing module/function.

- [ ] **Step 3: Move query and assembly logic out of route**

`routes/stocks.py` should become lightweight:

```python
def get_stock_research_payload(session, stock_code):
    raw = StockResearchReader(session).load(stock_code)
    if raw is None:
        return None
    return assemble_stock_research_payload(raw)
```

- [ ] **Step 4: Run old and new tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/api/test_pattern_insight_api.py tests/api/test_stock_research_assembler.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/api/readers/stock_research_reader.py apps/api/src/swinginsight/api/assemblers/stock_research_assembler.py apps/api/src/swinginsight/api/assemblers/pattern_insight_assembler.py apps/api/src/swinginsight/api/routes/stocks.py apps/api/tests/api/test_stock_research_assembler.py
git commit -m "refactor: split stock route into reader and assembler layers"
```

### Task 5: Replace Silent Prediction Fallback With Structured Reporting

**Files:**
- Modify: `apps/api/src/swinginsight/services/prediction_service.py`
- Modify: `apps/api/src/swinginsight/api/routes/predictions.py`
- Modify: `apps/api/tests/domain/test_prediction_service.py`

- [ ] **Step 1: Write failing fallback test**

```python
def test_prediction_reports_pattern_fallback_reason(session, monkeypatch):
    monkeypatch.setattr("...PatternSimilarityService.find_similar", lambda *_: (_ for _ in ()).throw(RuntimeError("boom")))
    result = PredictionService(session).predict("600010", date(2026, 4, 10))
    assert result.risk_flags["pattern_fallback_used"] == "true"
    assert "RuntimeError" in result.risk_flags["pattern_fallback_error_type"]
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_prediction_service.py -k fallback`  
Expected: FAIL.

- [ ] **Step 3: Implement structured fallback fields**

Add to `PredictionOutcome` and payload:

```python
fallback_used: bool
fallback_reason: str | None
fallback_error_type: str | None
fallback_stage: str | None
```

No broad silent swallow; map known degradations and record unexpected error types.

- [ ] **Step 4: Re-run prediction tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_prediction_service.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/services/prediction_service.py apps/api/src/swinginsight/api/routes/predictions.py apps/api/tests/domain/test_prediction_service.py
git commit -m "fix: replace silent prediction fallback with structured reporting"
```

### Task 6: Lock 5d/10d/20d Contracts Across API and UI

**Files:**
- Modify: `apps/api/src/swinginsight/api/routes/stocks.py`
- Modify: `apps/api/tests/api/test_pattern_insight_api.py`
- Modify: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/hooks/use-refresh-status.ts`
- Modify: `apps/web/src/app/stocks/[stockCode]/page.tsx`
- Create: `apps/web/tests/use-refresh-status.test.tsx`
- Modify: `apps/web/tests/stock-research-page-fetch.test.tsx`
- Modify: `README.md`

- [ ] **Step 1: Write failing contract and UI tests**

```python
def test_group_stat_horizon_contract_is_consistent(client):
    payload = client.get("/stocks/600157/group-stat").json()
    assert payload["horizon_days"] == [5, 10, 20]
    assert set(payload["return_distributions"].keys()) == {"5", "10", "20"}
```

```tsx
it("renders refresh status and handles missing 20d distribution", async () => {
  render(<StockResearchPage ... />);
  expect(await screen.findByText(/最近刷新/)).toBeTruthy();
});
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/api/test_pattern_insight_api.py`  
Run: `cd apps/web && pnpm test -- --run tests/stock-research-page-fetch.test.tsx tests/use-refresh-status.test.tsx`  
Expected: FAIL.

- [ ] **Step 3: Implement contract hardening + frontend refresh status polling**

`api.ts` additions:

```ts
startStockRefresh: (stockCode: string) => Promise<StockRefreshTaskData>;
getStockRefreshStatus: (stockCode: string) => Promise<StockRefreshStatusData>;
```

`use-refresh-status.ts` polls `/refresh-status` every 5s while `queued/running`.

- [ ] **Step 4: Run full targeted suites**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/api/test_pattern_insight_api.py tests/api/test_refresh_api.py tests/services/test_stock_refresh_service.py tests/domain/test_prediction_service.py`  
Run: `cd apps/web && pnpm test -- --run`  
Expected: PASS on all selected suites.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/api/routes/stocks.py apps/api/tests/api/test_pattern_insight_api.py apps/web/src/lib/api.ts apps/web/src/hooks/use-refresh-status.ts apps/web/src/app/stocks/[stockCode]/page.tsx apps/web/tests/use-refresh-status.test.tsx apps/web/tests/stock-research-page-fetch.test.tsx README.md
git commit -m "feat: lock horizon contracts and expose refresh status in ui"
```

### Task 7: End-to-End Verification and Final Integration Commit

**Files:**
- Modify: `README.md` (if command/output drift found during verification)

- [ ] **Step 1: Run backend verification set**

Run: `cd apps/api && ../../.venv/bin/pytest -q`  
Expected: PASS with no failures.

- [ ] **Step 2: Run frontend verification set**

Run: `cd apps/web && pnpm test -- --run && pnpm typecheck`  
Expected: PASS with no type errors.

- [ ] **Step 3: Manual API smoke**

Run:

```bash
curl -s -X POST http://127.0.0.1:8000/stocks/600010/refresh | jq .
curl -s http://127.0.0.1:8000/stocks/600010/refresh-status | jq .
curl -s http://127.0.0.1:8000/stocks/600010 | jq '.stock.stock_code'
```

Expected:
- refresh returns `task_id` and `status`.
- refresh-status shows stage rows.
- stock read returns data even if refresh has prior failure.

- [ ] **Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: update refresh observability and horizon contract runbook"
```

## Self-Review Checklist (Completed)

1. **Spec coverage:** All P0 requirements mapped to tasks (decoupling, observability, route refactor, fallback reporting, horizon contract).
2. **Placeholder scan:** No `TBD`/`TODO` placeholders in tasks.
3. **Type consistency:** Status enums and fallback field names are consistent across service/API/UI sections.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-16-p0-refresh-decoupling-and-contracts.md`. Two execution options:

1. Subagent-Driven (recommended) - I dispatch a fresh subagent per task, review between tasks, fast iteration
2. Inline Execution - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
