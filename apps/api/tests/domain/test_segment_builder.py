from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def turning_points():
    from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint

    return [
        DetectedTurningPoint(point_date=date(2024, 1, 4), point_type="trough", point_price=8.8, confirm_date=date(2024, 1, 5)),
        DetectedTurningPoint(point_date=date(2024, 1, 8), point_type="peak", point_price=10.6, confirm_date=date(2024, 1, 9)),
        DetectedTurningPoint(point_date=date(2024, 1, 10), point_type="trough", point_price=8.9, confirm_date=date(2024, 1, 11)),
    ]


def test_segment_builder_creates_up_and_down_swings() -> None:
    from swinginsight.domain.segments.builder import build_segments

    segments = build_segments(stock_code="000001", turning_points=turning_points(), version_code="zigzag@0.08")

    assert [segment.trend_direction for segment in segments] == ["up", "down"]
    assert segments[0].pct_change == 20.4545
    assert segments[0].duration_days == 4
    assert segments[1].pct_change == -16.0377
    assert segments[1].duration_days == 2


def test_segment_metrics_include_max_upside_and_drawdown() -> None:
    from swinginsight.domain.segments.metrics import compute_segment_metrics
    from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint

    start = DetectedTurningPoint(point_date=date(2024, 1, 4), point_type="trough", point_price=8.8, confirm_date=date(2024, 1, 5))
    end = DetectedTurningPoint(point_date=date(2024, 1, 8), point_type="peak", point_price=10.6, confirm_date=date(2024, 1, 9))
    price_window = [
        {"trade_date": date(2024, 1, 4), "high_price": 9.0, "low_price": 8.6, "close_price": 8.8},
        {"trade_date": date(2024, 1, 5), "high_price": 9.8, "low_price": 8.9, "close_price": 9.7},
        {"trade_date": date(2024, 1, 8), "high_price": 10.7, "low_price": 9.9, "close_price": 10.6},
    ]

    metrics = compute_segment_metrics(start=start, end=end, price_window=price_window)

    assert metrics["max_upside_pct"] == 21.5909
    assert metrics["max_drawdown_pct"] == -2.2727
    assert metrics["avg_daily_change_pct"] == 6.8182
