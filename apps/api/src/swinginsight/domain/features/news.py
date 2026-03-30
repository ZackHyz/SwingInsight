from __future__ import annotations

from collections.abc import Sequence

from swinginsight.services.segment_news_alignment_service import SegmentNewsTimelineItem


def compute_news_features(items: Sequence[SegmentNewsTimelineItem]) -> dict[str, float]:
    total = len(items)
    if total == 0:
        return {
            "news_count_before_trough_5d": 0.0,
            "news_count_after_peak_5d": 0.0,
            "positive_news_ratio": 0.0,
            "duplicate_news_ratio": 0.0,
        }

    before_trough = sum(1 for item in items if item.relation_type == "before_trough")
    after_peak = sum(1 for item in items if item.relation_type == "after_peak")
    positive_count = sum(1 for item in items if item.sentiment == "positive")
    duplicate_count = sum(1 for item in items if item.is_duplicate)

    return {
        "news_count_before_trough_5d": float(before_trough),
        "news_count_after_peak_5d": float(after_peak),
        "positive_news_ratio": positive_count / total,
        "duplicate_news_ratio": duplicate_count / total,
    }
