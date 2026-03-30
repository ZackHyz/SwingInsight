# Task 5 Research Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the minimum research page and manual turning point correction loop so a user can inspect one stock, edit final turning points, persist revision logs, and rebuild swing segments.

**Architecture:** Add a minimal FastAPI application that serves one aggregate stock research endpoint and one commit endpoint for final turning points. Add a lightweight Next-style page with SVG-based chart editing so the browser can modify a local final-point set and submit the full set back to the API.

**Tech Stack:** Python, FastAPI, SQLAlchemy, pytest, React, TypeScript, Vitest

---

### Task 1: Add backend API tests for research data and turning point commit

**Files:**
- Create: `apps/api/tests/api/test_turning_points.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_get_stock_research_payload_contains_expected_sections():
    response = client.get("/stocks/000001")
    assert response.status_code == 200
    assert "prices" in response.json()

def test_commit_turning_points_persists_logs_and_rebuilds_segments():
    response = client.post("/stocks/000001/turning-points/commit", json=payload)
    assert response.status_code == 200
    assert response.json()["rebuild_summary"]["segments"] >= 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && ../../.venv/bin/pytest tests/api/test_turning_points.py -v`
Expected: FAIL with missing API modules or routes.

- [ ] **Step 3: Write minimal implementation**

Create FastAPI app, schemas, and route handlers needed for the tests.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && ../../.venv/bin/pytest tests/api/test_turning_points.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/api apps/api/tests/api/test_turning_points.py apps/api/pyproject.toml
git commit -m "feat: add research api routes"
```

### Task 2: Add manual commit service and revision-log persistence

**Files:**
- Create: `apps/api/src/swinginsight/services/manual_turning_point_service.py`
- Modify: `apps/api/src/swinginsight/services/segment_generation_service.py`
- Modify: `apps/api/src/swinginsight/jobs/rebuild_segments.py`
- Test: `apps/api/tests/api/test_turning_points.py`

- [ ] **Step 1: Write the failing test for commit semantics**

```python
def test_commit_replaces_manual_final_points_and_logs_operations():
    response = client.post("/stocks/000001/turning-points/commit", json=payload)
    assert response.status_code == 200
    assert revision_logs == 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/api && ../../.venv/bin/pytest tests/api/test_turning_points.py::test_commit_turning_points_persists_logs_and_rebuilds_segments -v`
Expected: FAIL with missing service behavior.

- [ ] **Step 3: Write minimal implementation**

Persist manual final points, write `point_revision_log`, and rebuild segments from all `is_final=true` points.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/api && ../../.venv/bin/pytest tests/api/test_turning_points.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/services apps/api/src/swinginsight/jobs/rebuild_segments.py apps/api/tests/api/test_turning_points.py
git commit -m "feat: add manual turning point commit flow"
```

### Task 3: Add frontend page and editor component tests

**Files:**
- Create: `apps/web/src/components/kline-chart.tsx`
- Create: `apps/web/src/components/turning-point-editor.tsx`
- Create: `apps/web/src/components/trade-marker-layer.tsx`
- Create: `apps/web/src/lib/api.ts`
- Create: `apps/web/src/app/stocks/[stockCode]/page.tsx`
- Create: `apps/web/tests/turning-point-editor.test.tsx`

- [ ] **Step 1: Write the failing tests**

```tsx
it("lets the user select trough mode and save edits", () => {
  render(<TurningPointEditor ... />)
  expect(screen.getByRole("button", { name: "标记波谷" })).toBeInTheDocument()
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd apps/web && pnpm test -- --run`
Expected: FAIL with missing components.

- [ ] **Step 3: Write minimal implementation**

Build the research page, SVG chart, editor controls, and fetch wrapper.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd apps/web && pnpm test -- --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/web/src apps/web/tests apps/web/package.json apps/web/pnpm-lock.yaml
git commit -m "feat: add research page editor ui"
```

### Task 4: Verify end-to-end research page flow and finish Task 5

**Files:**
- Create: `apps/web/tests/e2e/turning-point-editor.spec.ts`
- Modify: `Makefile`
- Modify: `README.md`

- [ ] **Step 1: Write the failing flow test**

```ts
test("user can add and persist a trough point", async ({ page }) => {
  await page.goto("/stocks/000001")
  await page.getByRole("button", { name: "标记波谷" }).click()
  await page.getByTestId("kline-canvas").click({ position: { x: 420, y: 280 } })
  await page.getByRole("button", { name: "保存修正" }).click()
  await expect(page.getByText("保存成功")).toBeVisible()
})
```

- [ ] **Step 2: Run verification to see the initial failure**

Run: `cd apps/web && pnpm test -- --run`
Expected: existing unit tests pass; e2e spec is not yet wired or is pending.

- [ ] **Step 3: Wire final glue**

Document how to run the API and UI, add any missing test glue, and make the minimal integration path explicit.

- [ ] **Step 4: Run all relevant tests**

Run: `cd apps/api && ../../.venv/bin/pytest tests/test_smoke.py tests/db tests/ingest tests/domain tests/api -v`
Expected: PASS

Run: `cd apps/web && pnpm test -- --run`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/api apps/api/tests/api apps/web/src apps/web/tests Makefile README.md
git commit -m "feat: add research page and manual turning point correction"
```
