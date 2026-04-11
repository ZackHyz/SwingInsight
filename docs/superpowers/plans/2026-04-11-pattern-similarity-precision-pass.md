# Pattern Similarity Precision Pass Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove future leakage from pattern retrieval, improve representative window selection, and deduplicate similar-case results without changing the API schema.

**Architecture:** Keep the existing `PatternSimilarityService` as the orchestration layer. Add targeted pure helper methods for representative-window scoring, candidate filtering, payload construction, and result deduplication so behavior changes stay localized and testable.

**Tech Stack:** Python 3.12, SQLAlchemy ORM, pytest, FastAPI

---

### Task 1: Lock In Candidate Time Filtering

**Files:**
- Modify: `apps/api/tests/services/test_pattern_similarity_service.py`
- Modify: `apps/api/src/swinginsight/services/pattern_similarity_service.py`
- Test: `apps/api/tests/services/test_pattern_similarity_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pattern_similarity_service_excludes_future_windows_from_candidates() -> None:
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    segments = seed_prediction_context(session)

    for stock_code in {"000001", "600157"}:
        PatternWindowService(session).build_windows(stock_code=stock_code)
        PatternFeatureService(session).materialize(stock_code=stock_code)
        PatternWindowService(session).materialize_future_stats(stock_code=stock_code)

    current_segment = segments[0]
    result = PatternSimilarityService(session).find_similar_windows(current_segment=current_segment, top_k=20)

    assert result.query_window is not None
    query_start = result.query_window["start_date"]
    assert all(case.window_end_date < query_start for case in result.similar_cases if case.window_end_date is not None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_pattern_similarity_service_excludes_future_windows_from_candidates -q`
Expected: FAIL because current implementation returns windows after the query window.

- [ ] **Step 3: Write minimal implementation**

```python
candidates = self.session.scalars(
    select(PatternWindow)
    .where(
        PatternWindow.id != query_window.id,
        PatternWindow.end_date < query_window.start_date,
    )
    .order_by(PatternWindow.end_date.asc(), PatternWindow.id.asc())
).all()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_pattern_similarity_service_excludes_future_windows_from_candidates -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/services/test_pattern_similarity_service.py apps/api/src/swinginsight/services/pattern_similarity_service.py
git commit -m "fix: prevent future leakage in pattern similarity"
```

### Task 2: Improve Representative Window Selection

**Files:**
- Create or Modify: `apps/api/tests/services/test_pattern_similarity_service.py`
- Modify: `apps/api/src/swinginsight/services/pattern_similarity_service.py`
- Test: `apps/api/tests/services/test_pattern_similarity_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_select_representative_window_prefers_core_pattern_over_midpoint_only() -> None:
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService

    session = build_session()
    segments = seed_prediction_context(session)
    current_segment = segments[0]

    PatternWindowService(session).build_windows(stock_code=current_segment.stock_code)
    PatternFeatureService(session).materialize(stock_code=current_segment.stock_code)

    selected = PatternSimilarityService(session).select_representative_window(current_segment)

    assert selected is not None
    assert selected.window_size == 7
    assert selected.segment_id == current_segment.id
```
```

Then refine the assertion to target the expected core window dates based on the seeded fixture once the observed failure identifies the current midpoint-biased choice.

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_select_representative_window_prefers_core_pattern_over_midpoint_only -q`
Expected: FAIL because current implementation only uses midpoint proximity and pct gap.

- [ ] **Step 3: Write minimal implementation**

```python
def select_representative_window(self, current_segment: SwingSegment) -> PatternWindow | None:
    windows = ...
    if not windows:
        return None
    segment_rows = self._load_segment_price_rows(current_segment)
    segment_profile = self._build_segment_profile(segment_rows)
    ranked = sorted(
        windows,
        key=lambda window: (
            -self._representative_score(window=window, segment=current_segment, segment_profile=segment_profile),
            window.start_date,
            window.id,
        ),
    )
    return ranked[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_select_representative_window_prefers_core_pattern_over_midpoint_only -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/services/test_pattern_similarity_service.py apps/api/src/swinginsight/services/pattern_similarity_service.py
git commit -m "feat: score representative pattern windows by core trajectory"
```

### Task 3: Deduplicate Final Results By Segment And Stock

**Files:**
- Modify: `apps/api/tests/services/test_pattern_similarity_service.py`
- Modify: `apps/api/src/swinginsight/services/pattern_similarity_service.py`
- Test: `apps/api/tests/services/test_pattern_similarity_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_pattern_similarity_service_deduplicates_same_segment_results() -> None:
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    segments = seed_prediction_context(session)

    for stock_code in {"000001", "600157"}:
        PatternWindowService(session).build_windows(stock_code=stock_code)
        PatternFeatureService(session).materialize(stock_code=stock_code)
        PatternWindowService(session).materialize_future_stats(stock_code=stock_code)

    result = PatternSimilarityService(session).find_similar_windows(current_segment=segments[0], top_k=5)

    segment_ids = [case.segment_id for case in result.similar_cases if case.segment_id > 0]
    assert len(segment_ids) == len(set(segment_ids))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_pattern_similarity_service_deduplicates_same_segment_results -q`
Expected: FAIL because current implementation can return multiple windows from the same segment.

- [ ] **Step 3: Write minimal implementation**

```python
def _deduplicate_cases(self, cases: list[SimilarCase], top_k: int) -> list[SimilarCase]:
    accepted: list[SimilarCase] = []
    seen_segments: set[int] = set()
    stock_counts: dict[str, int] = {}
    for case in cases:
        if case.segment_id > 0 and case.segment_id in seen_segments:
            continue
        if stock_counts.get(case.stock_code, 0) >= 2:
            continue
        accepted.append(case)
        if case.segment_id > 0:
            seen_segments.add(case.segment_id)
        stock_counts[case.stock_code] = stock_counts.get(case.stock_code, 0) + 1
        if len(accepted) >= top_k:
            break
    return accepted
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_pattern_similarity_service_deduplicates_same_segment_results -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/services/test_pattern_similarity_service.py apps/api/src/swinginsight/services/pattern_similarity_service.py
git commit -m "feat: deduplicate pattern similarity results"
```

### Task 4: Use Real Window Turning Points In Candle Scoring

**Files:**
- Modify: `apps/api/tests/services/test_pattern_similarity_service.py`
- Modify: `apps/api/src/swinginsight/services/pattern_similarity_service.py`
- Test: `apps/api/tests/services/test_pattern_similarity_service.py`

- [ ] **Step 1: Write the failing test**

```python
def test_feature_payload_uses_window_turning_points_instead_of_price_seq_extrema() -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternWindow
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService

    session = build_session()
    window = PatternWindow(
        window_uid="pw-test-000001-2024-01-01-2024-01-09",
        stock_code="000001",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 9),
        window_size=7,
        start_close=10.0,
        end_close=10.4,
        period_pct_change=4.0,
        highest_day_pos=1,
        lowest_day_pos=5,
        trend_label="sideways",
        feature_version="pattern:v1",
    )
    feature = PatternFeature(
        window_id=1,
        price_seq_json=[1.0, 0.99, 1.02, 1.03, 1.01, 1.00, 1.04],
        candle_feat_json=[0.1] * 35,
        volume_seq_json=[1.0] * 7,
        turnover_seq_json=[1.0] * 7,
        trend_context_json=[1.0] * 10,
        vola_context_json=[0.1] * 5,
        coarse_vector_json=[0.0] * 21,
        feature_version="pattern:v1",
    )

    payload = PatternSimilarityService(session)._feature_payload(window, feature)

    assert payload["highest_day_pos"] == 1
    assert payload["lowest_day_pos"] == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_feature_payload_uses_window_turning_points_instead_of_price_seq_extrema -q`
Expected: FAIL because current implementation derives turning points from `price_seq`.

- [ ] **Step 3: Write minimal implementation**

```python
def _feature_payload(self, window: PatternWindow, row: PatternFeature) -> dict[str, object]:
    ...
    return {
        "highest_day_pos": int(window.highest_day_pos or 0),
        "lowest_day_pos": int(window.lowest_day_pos or 0),
        ...
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `.venv/bin/pytest apps/api/tests/services/test_pattern_similarity_service.py::test_feature_payload_uses_window_turning_points_instead_of_price_seq_extrema -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add apps/api/tests/services/test_pattern_similarity_service.py apps/api/src/swinginsight/services/pattern_similarity_service.py
git commit -m "fix: use stored turning points for candle similarity"
```

### Task 5: Verify Integration Behavior

**Files:**
- Modify: `apps/api/tests/integration/test_pattern_similarity_flow.py`
- Test: `apps/api/tests/integration/test_pattern_similarity_flow.py`

- [ ] **Step 1: Extend the integration test**

```python
assert payload["query_window"]["window_size"] == 7
query_start = payload["query_window"]["start_date"]
segment_ids = [item["segment_id"] for item in payload["similar_cases"] if item["segment_id"] is not None and item["segment_id"] > 0]
assert len(segment_ids) == len(set(segment_ids))
assert all(
    item["window_end_date"] < query_start
    for item in payload["similar_cases"]
    if item["window_end_date"] is not None
)
```

- [ ] **Step 2: Run test to verify behavior**

Run: `.venv/bin/pytest apps/api/tests/integration/test_pattern_similarity_flow.py -q`
Expected: PASS

- [ ] **Step 3: Run focused regression suite**

Run: `.venv/bin/pytest apps/api/tests/domain/test_pattern_similarity.py apps/api/tests/services/test_pattern_similarity_service.py apps/api/tests/integration/test_pattern_similarity_flow.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add apps/api/tests/integration/test_pattern_similarity_flow.py apps/api/tests/services/test_pattern_similarity_service.py apps/api/src/swinginsight/services/pattern_similarity_service.py
git commit -m "test: cover pattern similarity precision pass"
```
