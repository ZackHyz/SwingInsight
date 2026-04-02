from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_compute_news_features_includes_sentiment_heat_and_event_flags() -> None:
    from swinginsight.domain.features.news import NewsFeatureItem, compute_news_features

    items = [
        NewsFeatureItem(
            relation_type="before_trough",
            sentiment="positive",
            is_duplicate=False,
            category="announcement",
            heat_level="high",
        ),
        NewsFeatureItem(
            relation_type="after_peak",
            sentiment="negative",
            is_duplicate=True,
            category="media_news",
            heat_level="medium",
        ),
    ]

    features = compute_news_features(items)

    assert features["positive_news_ratio"] == 0.5
    assert features["duplicate_news_ratio"] == 0.5
    assert features["high_heat_news_ratio"] == 0.5
    assert features["announcement_count_before_trough_5d"] == 1.0
    assert features["negative_news_count_after_peak_5d"] == 1.0
    assert features["has_earnings_event"] == 0.0
    assert features["has_risk_alert"] == 0.0
