from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence

@dataclass(slots=True, frozen=True)
class NewsFeatureItem:
    relation_type: str
    sentiment: str | None
    is_duplicate: bool
    category: str | None = None
    heat_level: str | None = None
    sub_category: str | None = None


def compute_news_features(items: Sequence[NewsFeatureItem]) -> dict[str, float]:
    total = len(items)
    if total == 0:
        return {
            "news_count_before_trough_5d": 0.0,
            "news_count_after_peak_5d": 0.0,
            "announcement_count_before_trough_5d": 0.0,
            "negative_news_count_after_peak_5d": 0.0,
            "positive_news_ratio": 0.0,
            "duplicate_news_ratio": 0.0,
            "high_heat_news_ratio": 0.0,
            "has_earnings_event": 0.0,
            "has_risk_alert": 0.0,
        }

    before_trough = sum(1 for item in items if item.relation_type == "before_trough")
    after_peak = sum(1 for item in items if item.relation_type == "after_peak")
    announcement_before_trough = sum(
        1 for item in items if item.relation_type == "before_trough" and item.category == "announcement"
    )
    negative_after_peak = sum(1 for item in items if item.relation_type == "after_peak" and item.sentiment == "negative")
    positive_count = sum(1 for item in items if item.sentiment == "positive")
    duplicate_count = sum(1 for item in items if item.is_duplicate)
    high_heat_count = sum(1 for item in items if item.heat_level == "high")
    has_earnings_event = any(item.sub_category == "earnings" for item in items)
    has_risk_alert = any(item.sub_category == "risk_alert" for item in items)

    return {
        "news_count_before_trough_5d": float(before_trough),
        "news_count_after_peak_5d": float(after_peak),
        "announcement_count_before_trough_5d": float(announcement_before_trough),
        "negative_news_count_after_peak_5d": float(negative_after_peak),
        "positive_news_ratio": positive_count / total,
        "duplicate_news_ratio": duplicate_count / total,
        "high_heat_news_ratio": high_heat_count / total,
        "has_earnings_event": 1.0 if has_earnings_event else 0.0,
        "has_risk_alert": 1.0 if has_risk_alert else 0.0,
    }
