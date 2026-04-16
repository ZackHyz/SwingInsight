# P1 Evaluation And Research Upgrades Design

## Scope Decision

This P1 request contains five independent subprojects:

1. Batch evaluation suite (evaluation-before-feature workflow)
2. News-event labeling quality improvements
3. Provisional-extrema visualization
4. SimilarCasesTimeline drill-down upgrade
5. Nightly market scan + ranked watchlist entry

To keep delivery incremental and testable, execution is split:

- **Implement now:** Subproject 1 (batch evaluation suite)
- **Design now, implement later:** Subprojects 2-5

This allows immediate quality governance on algorithm changes while preserving clear execution lanes for product upgrades.

## Goals

- Make evaluation reproducible with a fixed, versioned sample pool.
- Produce one Markdown report per run covering turning points, pattern ranking, and calibration.
- Answer reliability by stock category, not only by single-symbol examples.
- Prepare implementation-ready designs for P1 items 7-10.

## Non-Goals (Current Execution Cycle)

- No CI/PR blocking integration for batch evaluation (local one-command only).
- No changes to existing public API contracts in this cycle except where future designs explicitly describe them.
- No implementation of items 7-10 in this cycle.

---

## Subproject 1: Batch Evaluation Suite (Implement Now)

### Functional Requirements

- Fixed sample pool file with 4 categories, 10 symbols each:
  - trend names
  - range names
  - announcement-heavy names
  - low-liquidity names
- One local command to run complete evaluation pipeline.
- Markdown report output with timestamped filename.
- Three evaluation blocks:
  - turning point quality
  - pattern ranking quality
  - calibration quality (before/after)

### File Layout

- Create: `apps/api/config/evaluation/sample_pool.v1.json`
- Create: `apps/api/src/swinginsight/services/batch_evaluation_service.py`
- Create: `apps/api/scripts/run_batch_evaluation.py`
- Create: `apps/api/tests/services/test_batch_evaluation_service.py`
- Create: `apps/api/tests/scripts/test_run_batch_evaluation.py`
- Create output dir (runtime): `apps/api/reports/evaluation/`

### Data Contracts

Sample pool JSON:

```json
{
  "version": "v1",
  "categories": {
    "trend_names": [
      { "stock_code": "600000", "stock_name": "xx", "note": "optional" }
    ],
    "range_names": [],
    "announcement_heavy_names": [],
    "low_liquidity_names": []
  }
}
```

Report filename:

- `apps/api/reports/evaluation/batch-eval-YYYYMMDD-HHMM.md`

### Metric Definitions (Locked)

Turning point (per symbol, per category aggregate):

- `final_count`: count of `turning_point.is_final=true`
- `system_count`: count of `turning_point.source_type=system`
- `exact_match_precision`: matched(system->final, same date+type) / system_count
- `exact_match_recall`: matched(final<-system, same date+type) / final_count
- `f1_exact`: harmonic mean of precision/recall
- `tolerance_match_recall_2d`: final matched by system within +/-2 trading days and same type / final_count
- `median_confirm_lag_days`: median(`confirm_date - point_date`) over system points with non-null confirm date

Pattern ranking (horizon 5/10/20):

- Reuse backtest summary fields:
  - `rows`
  - `coverage_rate`
  - `brier_score`
  - `sample_count_distribution`
  - `tiers`
- Add:
  - `win_rate_observed`
  - `avg_predicted_win_rate`
  - `calibration_gap = abs(avg_predicted_win_rate - win_rate_observed)`

Calibration (horizon 5/10/20):

- `brier_before`, `brier_after`, `delta_brier = brier_after - brier_before`
- `is_monotonic`
- bucket error comparison:
  - `mean_abs_bucket_error_before`
  - `mean_abs_bucket_error_after`
  - `bucket_error_delta`

Reliability ranking (by category):

- Weighted score from:
  - `coverage_rate`
  - `brier_after` (inverse contribution)
  - `f1_exact`
- Output `reliability_rank` where 1 is most reliable category.

### Execution Command

```bash
cd apps/api
../../.venv/bin/python scripts/run_batch_evaluation.py \
  --sample-pool config/evaluation/sample_pool.v1.json
```

Optional arguments (v1):

- `--start YYYY-MM-DD`
- `--end YYYY-MM-DD`
- `--horizons 5 10 20` (default fixed to 5/10/20)
- `--report-path` (override output path)

### Error Handling

- Missing symbol data does not abort whole run.
- Per-symbol failures are captured in a `failures` section in report.
- Final exit code:
  - `0` when at least one symbol successfully evaluated
  - non-zero only if no symbol can be evaluated or input config invalid.

### Testing Strategy

- Service tests:
  - metric computations
  - reliability ranking
  - tolerant match logic (+/-2 days)
- Script tests:
  - sample-pool parsing
  - report file generation
  - key markdown sections rendered
  - partial-failure behavior

---

## Subproject 2: News-Event Labeling Quality (Design Only)

### Objective

Reduce noisy tags on announcement-heavy symbols and lower false-positive `event_conflict_flag`.

### Design

- Extend event rule granularity:
  - announcement rules
  - media report rules
  - rumor/market-chatter rules
- Add conflict merge policy:
  - same-day duplicate event collapse
  - source-priority resolution
  - confidence-based dominance on contradictory labels
- Add noise suppression for high-frequency template announcements:
  - board meeting notices
  - routine disclosure templates
  - low-information repeated bulletins

### Implementation Targets (Future)

- `apps/api/src/swinginsight/domain/news/events.py`
- `apps/api/src/swinginsight/domain/news/tagging.py`
- `apps/api/src/swinginsight/services/news_processing_service.py`
- new evaluation helper for sampled review set

### Validation Plan (Future)

- Manual review set: 100-200 sampled items
- Compare before/after:
  - noise-tag ratio
  - conflict false-positive ratio
  - useful-event recall on announcement-heavy stocks

---

## Subproject 3: Provisional-Extrema Visualization (Design Only)

### Objective

Make unconfirmed extrema explicit on research page so users can distinguish confirmed turning structure from potential turning observations.

### Design

- Add provisional marker type on Kline chart.
- Tooltip text:
  - `候选高点/低点，尚未确认反转`
- UI copy split:
  - confirmed turning points
  - provisional extrema

### Implementation Targets (Future)

- `apps/web/src/components/kline-chart.tsx`
- `apps/web/src/app/stocks/[stockCode]/page.tsx`
- API payload extension if provisional extrema are not currently exposed

### Validation Plan (Future)

- Component tests for marker rendering and tooltip text.
- Interaction test ensuring both semantics can co-exist in one chart.

---

## Subproject 4: SimilarCases Drill-Down Upgrade (Design Only)

### Objective

Turn similar cases from static display into a research workflow tool.

### Design

- Each case can open segment detail.
- Side-by-side view:
  - query window
  - matched historical window
- Add context fields:
  - 5/10/20 forward outcomes
  - event summary
  - same-symbol vs cross-symbol indicator
- Add ranking modes:
  - same-symbol first
  - similarity first
  - sample-quality first

### Implementation Targets (Future)

- `apps/web/src/components/similar-case-list.tsx`
- `apps/web/src/components/prediction-panel.tsx`
- `apps/web/src/hooks/use-pattern-insight.ts`
- potential API enrichments in similar-cases endpoint

### Validation Plan (Future)

- unit tests for ranking modes
- integration tests for drill-down navigation and side-by-side rendering

---

## Subproject 5: Nightly Market Scan + Watchlist (Design Only)

### Objective

Move from code-first query flow to candidate-pool-first workflow.

### Design

- Nightly batch scan on full market or configured universe.
- Produce watchlist rows with:
  - pattern score
  - sample_count
  - confidence
  - event density
  - latest refresh timestamp
- Add landing entry for ranked watchlist.

### Implementation Targets (Future)

- backend batch job + persistence table for scan results
- API endpoint for watchlist retrieval
- web home/library entry for ranked candidates

### Validation Plan (Future)

- nightly job deterministic smoke on demo/universe subset
- watchlist endpoint contract tests
- front-end rendering tests for empty/partial/full leaderboard

---

## Rollout Plan

Phase A (current):

- Implement Subproject 1 end-to-end.
- Update README with batch-evaluation command and report example.

Phase B (next):

- Execute Subproject 2 with sampled review framework first.

Phase C:

- Execute Subprojects 3 and 4 together for UX consistency.

Phase D:

- Execute Subproject 5 after baseline evaluation coverage is stable.

## Risks

- Symbol data completeness differs across categories; sparse symbols may bias reliability score.
- Calibration may fail for symbols with insufficient backtest rows; must degrade gracefully.
- Turning-point metric quality depends on presence of final/manual points.

## Mitigations

- Explicitly surface per-symbol eligibility and skip reasons in report.
- Keep reliability ranking based on eligible sample counts with transparency.
- Add threshold warnings for low-support categories.
