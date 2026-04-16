# P1 Batch Evaluation Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a one-command local batch evaluation workflow that runs turning-point, pattern ranking, and calibration assessments on a fixed 4x10 sample pool and emits a Markdown report.

**Architecture:** Add a versioned sample-pool config, implement a service layer that computes evaluation metrics and report markdown, and expose a script entrypoint for execution. Reuse existing backtest/calibration services and isolate report rendering in one module.

**Tech Stack:** Python 3.12, SQLAlchemy ORM, existing SwingInsight services/jobs, pytest.

---

## File Structure

- Create: `apps/api/config/evaluation/sample_pool.v1.json`
- Create: `apps/api/src/swinginsight/services/batch_evaluation_service.py`
- Create: `apps/api/scripts/run_batch_evaluation.py`
- Create: `apps/api/tests/services/test_batch_evaluation_service.py`
- Create: `apps/api/tests/scripts/test_run_batch_evaluation.py`
- Modify: `README.md`

### Task 1: Add Versioned Sample Pool Config

**Files:**
- Create: `apps/api/config/evaluation/sample_pool.v1.json`
- Create: `apps/api/tests/scripts/test_run_batch_evaluation.py`

- [ ] **Step 1: Write failing script-config test**

```python
def test_load_sample_pool_requires_four_categories(tmp_path):
    ...
    with pytest.raises(ValueError):
        load_sample_pool(bad_path)
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/scripts/test_run_batch_evaluation.py -k sample_pool`  
Expected: FAIL due to missing script/parser.

- [ ] **Step 3: Add v1 sample pool file with 4 categories and 10 symbols each**

Create `sample_pool.v1.json` with:
- `version: "v1"`
- `trend_names`, `range_names`, `announcement_heavy_names`, `low_liquidity_names`
- each category has 10 entries.

- [ ] **Step 4: Add minimal script loader and category validation**

`run_batch_evaluation.py`:
- `load_sample_pool(path: Path) -> dict[str, list[dict[str, str]]]`
- validate exact 4 category keys.

- [ ] **Step 5: Re-run script-config test**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/scripts/test_run_batch_evaluation.py -k sample_pool`  
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add apps/api/config/evaluation/sample_pool.v1.json apps/api/scripts/run_batch_evaluation.py apps/api/tests/scripts/test_run_batch_evaluation.py
git commit -m "feat: add versioned sample pool config for batch evaluation"
```

### Task 2: Implement Turning-Point Metrics in Service

**Files:**
- Create: `apps/api/src/swinginsight/services/batch_evaluation_service.py`
- Create: `apps/api/tests/services/test_batch_evaluation_service.py`

- [ ] **Step 1: Write failing turning-point metric tests**

```python
def test_turning_point_metrics_compute_exact_and_tolerance_recall(session):
    metrics = BatchEvaluationService(session).evaluate_turning_points("600001")
    assert metrics["f1_exact"] >= 0.0
    assert metrics["tolerance_match_recall_2d"] >= metrics["exact_match_recall"]
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_batch_evaluation_service.py -k turning_point`  
Expected: FAIL due to missing service implementation.

- [ ] **Step 3: Implement turning-point metric computation**

In `batch_evaluation_service.py`:
- load `is_final=True` and `source_type=system` turning points
- compute `final_count`, `system_count`, `exact_match_precision`, `exact_match_recall`, `f1_exact`
- compute `tolerance_match_recall_2d`
- compute `median_confirm_lag_days`

- [ ] **Step 4: Re-run turning-point tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_batch_evaluation_service.py -k turning_point`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/services/batch_evaluation_service.py apps/api/tests/services/test_batch_evaluation_service.py
git commit -m "feat: add turning-point metrics for batch evaluation"
```

### Task 3: Implement Pattern Ranking + Calibration Aggregation

**Files:**
- Modify: `apps/api/src/swinginsight/services/batch_evaluation_service.py`
- Modify: `apps/api/tests/services/test_batch_evaluation_service.py`

- [ ] **Step 1: Write failing aggregation tests**

```python
def test_pattern_and_calibration_metrics_include_horizons(session, monkeypatch):
    report = BatchEvaluationService(session).evaluate_stock("600001", ...)
    assert set(report["pattern"].keys()) == {5, 10, 20}
    assert set(report["calibration"].keys()) == {5, 10, 20}
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_batch_evaluation_service.py -k calibration`  
Expected: FAIL.

- [ ] **Step 3: Implement pattern/calibration integration**

Service methods:
- run backtest for horizons 5/10/20
- compute observed/predicted/gap metrics
- run calibration fit+verify per horizon
- compute bucket error before/after means and deltas

- [ ] **Step 4: Re-run service tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_batch_evaluation_service.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/src/swinginsight/services/batch_evaluation_service.py apps/api/tests/services/test_batch_evaluation_service.py
git commit -m "feat: aggregate pattern ranking and calibration metrics"
```

### Task 4: Implement Script Entrypoint + Markdown Report

**Files:**
- Modify: `apps/api/scripts/run_batch_evaluation.py`
- Modify: `apps/api/tests/scripts/test_run_batch_evaluation.py`

- [ ] **Step 1: Write failing markdown output test**

```python
def test_script_writes_markdown_report(tmp_path, monkeypatch):
    ...
    assert report_path.exists()
    assert "Turning Point Evaluation" in report_path.read_text()
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/scripts/test_run_batch_evaluation.py -k markdown`  
Expected: FAIL.

- [ ] **Step 3: Implement script orchestration and report writing**

Script should:
- parse args (`--sample-pool`, `--start`, `--end`, `--horizons`, `--report-path`)
- run batch service over all categories/stocks
- write markdown to timestamped path under `reports/evaluation` if not overridden
- return 0 if at least one stock succeeds, else non-zero

- [ ] **Step 4: Re-run script tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/scripts/test_run_batch_evaluation.py`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add apps/api/scripts/run_batch_evaluation.py apps/api/tests/scripts/test_run_batch_evaluation.py
git commit -m "feat: add batch evaluation script and markdown reporting"
```

### Task 5: Update README and Run Verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add batch evaluation usage docs**

Add command example and report output location in README.

- [ ] **Step 2: Run targeted backend tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_batch_evaluation_service.py tests/scripts/test_run_batch_evaluation.py`  
Expected: PASS.

- [ ] **Step 3: Run full backend tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q`  
Expected: PASS.

- [ ] **Step 4: Final commit**

```bash
git add README.md
git commit -m "docs: add batch evaluation workflow for p1"
```

## Self-Review Checklist (Completed)

1. **Spec coverage:** Subproject 1 requirements mapped to sample pool, service metrics, script, report, docs.
2. **Placeholder scan:** No `TBD` or unresolved task placeholders.
3. **Type consistency:** Horizon and metric keys align with spec definitions.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-16-p1-batch-evaluation-suite.md`.  
Proceeding with **Inline Execution** in this session using `executing-plans`.
