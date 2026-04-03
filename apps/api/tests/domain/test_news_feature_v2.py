from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_adjusted_sentiment_rewards_positive_news_before_trough() -> None:
    from swinginsight.services.news_sentiment_service import adjust_sentiment_with_position

    sentiment = adjust_sentiment_with_position(
        base_score=0.6,
        category="announcement",
        relation_type="before_trough",
        point_type="trough",
        heat_score=0.45,
        event_types=["earnings"],
    )

    assert sentiment > 0.6


def test_compute_news_features_emits_adjusted_sentiment_metrics() -> None:
    from swinginsight.domain.features.news import NewsFeatureItem, compute_news_features

    features = compute_news_features(
        [
            NewsFeatureItem(
                relation_type="before_trough",
                sentiment="positive",
                is_duplicate=False,
                category="announcement",
                heat_level="medium",
                sentiment_score_adjusted=0.75,
                event_conflict_flag=False,
                event_types=["earnings"],
            ),
            NewsFeatureItem(
                relation_type="after_peak",
                sentiment="negative",
                is_duplicate=False,
                category="announcement",
                heat_level="high",
                sentiment_score_adjusted=-0.8,
                event_conflict_flag=True,
                event_types=["capital_action"],
            ),
        ]
    )

    assert features["avg_adjusted_sentiment_before_trough_5d"] == 0.75
    assert features["avg_adjusted_sentiment_after_peak_5d"] == -0.8
    assert features["conflicting_event_ratio"] == 0.5
    assert features["capital_action_risk_flag"] == 1.0
