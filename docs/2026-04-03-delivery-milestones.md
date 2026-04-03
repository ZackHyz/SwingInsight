# 2026-04-03 Delivery Milestones

## Scope

This document summarizes the current delivered batch that has already been pushed to `main`.

Primary focus in this batch:

- News module real-data integration
- News sentiment and event extraction
- Pattern-based similarity engine v1
- Research page and API alignment
- Turning point confirmation semantics cleanup

Latest synced commit:

- `41d85d0 feat: add news sentiment and pattern similarity engine`

## Milestone 1: Real News Data Pipeline

Completed:

- Connected real news sources for stock news and announcements
- Added incremental import flow for research-page driven refresh
- Added processing, deduplication, and alignment with points and segments
- Added CLI entrypoints for import, processing, alignment, and backfill

Outcome:

- Research data is no longer limited to demo-only news records
- Announcement and media news can enter the same downstream processing chain

## Milestone 2: News Sentiment and Event Structuring

Completed:

- Added `news_sentiment_result` and `news_event_result`
- Added rule-based event extraction and sentiment scoring
- Added adjusted sentiment, conflict flag, and event typing
- Added governance-event handling for announcement-heavy cases

Outcome:

- News is no longer only a list item; it is now a structured signal source
- Research page can display category, tags, event types, and adjusted sentiment
- Downstream features can consume sentiment/event counts instead of raw headlines only

## Milestone 3: Pattern Similarity Engine V1

Completed:

- Added `pattern_window`, `pattern_feature`, `pattern_future_stat`, `pattern_match_result`
- Added fixed `7`-day window generation
- Added pattern feature materialization and future-return statistics
- Added representative-window selection, coarse recall, and fine ranking
- Added query-window payload and grouped future-return statistics

Outcome:

- Similarity search is no longer only segment-to-segment
- Current search now has window-level comparison, more explicit scoring dimensions, and better future-performance summaries

## Milestone 4: Research Page and Comparison UX Alignment

Completed:

- Similar cases now distinguish similar window vs owning historical segment
- Comparison dialog now centers on the actual query window
- Pattern scores such as candle, trend context, and volatility are carried through the API
- News summary on the page is aligned with the currently displayed news list instead of a mismatched summary window

Outcome:

- Similar-case explanations are closer to what the model actually compares
- News and similarity sections are less misleading at the UI layer

## Milestone 5: Live Refresh and Data Resilience

Completed:

- Existing stocks can refresh latest day price data instead of only bootstrapping missing stocks
- Pattern artifacts are auto-created and materialized when missing
- Pattern prediction path has guarded fallback behavior
- News refresh path retries once after duplicate-event write races

Outcome:

- Research-page load is more stable during local iteration and incremental refresh
- Missing pattern tables or partial pattern artifacts no longer silently degrade the page as easily

## Milestone 6: Turning Point Semantics Correction

Completed:

- Clarified that an unfinished tail move must not be treated as a confirmed peak/trough
- Tightened persistence so only confirmed turning points are stored and shown in research payloads
- Rebuilt `600010` with the corrected semantics

Outcome:

- A latest price high without reverse confirmation is no longer mislabeled as a final peak
- For `600010`, the latest confirmed turning point is now the `2026-03-23` trough instead of incorrectly showing an unconfirmed April peak

## Verification Snapshot

Key verification completed during this batch:

- `apps/api/tests/domain/test_turning_points.py`
- `apps/api/tests/api/test_turning_points_api.py`
- `apps/api/tests/services/test_stock_research_service.py`
- `apps/api/tests/domain/test_prediction_service.py`
- `apps/api/tests/ingest/test_job_cli.py`
- `apps/api/tests/services/test_news_sentiment_service.py`
- `apps/api/tests/domain/test_news_processing.py`
- `apps/api/tests/integration/test_pattern_similarity_flow.py`

Representative passing runs:

- `31 passed` for turning point, research service, prediction, API, and CLI regression coverage
- `4 passed` for news sentiment and news processing focused coverage

Runtime verification performed:

- Research API was exercised against `600010`
- Final turning points were checked after rebuild
- Research-page endpoint and front-end route were both reachable locally

## Current State

What is in place now:

- Real news ingestion exists
- News sentiment/event structuring exists
- Pattern similarity engine v1 exists
- Research page consumes the new API structures
- Confirmed turning-point semantics are corrected for the latest tail move case

What still remains as follow-up work:

- Optional visual distinction for provisional highs/lows vs confirmed turning points
- More robust idempotency deeper inside news event persistence instead of only retrying at the research refresh layer
- Further tuning of pattern ranking quality with more live-sample review

## Recommended Next Steps

- Add explicit provisional-extrema visualization if the product needs “current possible top/bottom” hints
- Expand pattern-ranking evaluation with broader live-market samples
- Continue tightening news-event labeling quality for announcement-heavy names
- Add a dedicated release-note or changelog track if future batches need the same delivery summary format
