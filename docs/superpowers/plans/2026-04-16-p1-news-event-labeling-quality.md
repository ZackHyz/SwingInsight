# P1 News-Event Labeling Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce noisy tags on announcement-heavy symbols and lower false-positive `event_conflict_flag` in backend news labeling.

**Architecture:** Evolve rule extraction in `events.py` to support source-aware confidence, add merge policy in sentiment service for same-type contradictory signals, and tighten batch grouping to collapse same-day duplicate cross-source headlines. Keep current DB schema/API contract unchanged.

**Tech Stack:** Python 3.12, SQLAlchemy ORM, pytest.

---

## File Structure

- Modify: `apps/api/src/swinginsight/domain/news/events.py`
- Modify: `apps/api/src/swinginsight/services/news_sentiment_service.py`
- Modify: `apps/api/src/swinginsight/services/news_processing_service.py`
- Modify: `apps/api/tests/domain/test_news_sentiment_rules.py`
- Modify: `apps/api/tests/services/test_news_sentiment_service.py`
- Modify: `apps/api/tests/domain/test_news_processing.py`

### Task 1: Add Failing Tests For Source-Aware Event Rules

**Files:**
- Modify: `apps/api/tests/domain/test_news_sentiment_rules.py`

- [ ] **Step 1: Add failing tests for source-aware extraction and governance-noise suppression**

```python
def test_extract_events_prefers_announcement_confidence_for_same_keyword() -> None:
    ...

def test_extract_events_suppresses_template_governance_noise() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_news_sentiment_rules.py -k "source_aware or governance_noise"`
Expected: FAIL.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/domain/test_news_sentiment_rules.py
git commit -m "test: add failing coverage for source-aware event extraction"
```

### Task 2: Implement Source-Aware Rules And Noise Suppression

**Files:**
- Modify: `apps/api/src/swinginsight/domain/news/events.py`
- Modify: `apps/api/tests/domain/test_news_sentiment_rules.py`

- [ ] **Step 1: Implement source-aware rule metadata and confidence on extracted signals**

- [ ] **Step 2: Implement governance template suppression for routine disclosures**

- [ ] **Step 3: Re-run targeted tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_news_sentiment_rules.py -k "source_aware or governance_noise"`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/swinginsight/domain/news/events.py apps/api/tests/domain/test_news_sentiment_rules.py
git commit -m "feat: add source-aware event rules and governance noise suppression"
```

### Task 3: Add Failing Tests For Merge Policy And Conflict Flag

**Files:**
- Modify: `apps/api/tests/services/test_news_sentiment_service.py`

- [ ] **Step 1: Add failing tests for source-priority resolution and confidence dominance**

```python
def test_merge_events_prefers_higher_priority_source() -> None:
    ...

def test_merge_events_degrades_to_neutral_when_confidence_close() -> None:
    ...
```

- [ ] **Step 2: Run tests to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_news_sentiment_service.py -k "merge_events or confidence_close"`
Expected: FAIL.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/services/test_news_sentiment_service.py
git commit -m "test: add failing coverage for event merge policy"
```

### Task 4: Implement Merge Policy In Sentiment Service

**Files:**
- Modify: `apps/api/src/swinginsight/services/news_sentiment_service.py`
- Modify: `apps/api/tests/services/test_news_sentiment_service.py`

- [ ] **Step 1: Implement same-type merge helper using source-priority and confidence-dominance**

- [ ] **Step 2: Apply merged events before scoring/persisting results**

- [ ] **Step 3: Re-run sentiment-service tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/services/test_news_sentiment_service.py`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/api/src/swinginsight/services/news_sentiment_service.py apps/api/tests/services/test_news_sentiment_service.py
git commit -m "feat: add merge policy for contradictory event labels"
```

### Task 5: Add Failing Tests For Same-Day Duplicate Collapse In Processing

**Files:**
- Modify: `apps/api/tests/domain/test_news_processing.py`

- [ ] **Step 1: Add failing test for cross-source same-day duplicate collapse behavior**

```python
def test_process_news_collapses_same_day_cross_source_duplicates() -> None:
    ...
```

- [ ] **Step 2: Run test to verify failure**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_news_processing.py -k cross_source`
Expected: FAIL.

- [ ] **Step 3: Commit**

```bash
git add apps/api/tests/domain/test_news_processing.py
git commit -m "test: add failing coverage for same-day cross-source dedupe"
```

### Task 6: Implement Processing Grouping Update And Final Verification

**Files:**
- Modify: `apps/api/src/swinginsight/services/news_processing_service.py`
- Modify: `apps/api/tests/domain/test_news_processing.py`

- [ ] **Step 1: Update batch grouping key to collapse same-day cross-source headline duplicates**

- [ ] **Step 2: Re-run targeted news tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q tests/domain/test_news_sentiment_rules.py tests/services/test_news_sentiment_service.py tests/domain/test_news_processing.py`
Expected: PASS.

- [ ] **Step 3: Run full backend tests**

Run: `cd apps/api && ../../.venv/bin/pytest -q`
Expected: PASS.

- [ ] **Step 4: Final commit**

```bash
git add apps/api/src/swinginsight/domain/news/events.py apps/api/src/swinginsight/services/news_sentiment_service.py apps/api/src/swinginsight/services/news_processing_service.py apps/api/tests/domain/test_news_sentiment_rules.py apps/api/tests/services/test_news_sentiment_service.py apps/api/tests/domain/test_news_processing.py
git commit -m "feat: improve news-event labeling quality for announcement-heavy cases"
```
