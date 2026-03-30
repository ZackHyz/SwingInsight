from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def sample_price_series():
    return [
        {"trade_date": date(2024, 1, 2), "close_price": 10.0},
        {"trade_date": date(2024, 1, 3), "close_price": 9.4},
        {"trade_date": date(2024, 1, 4), "close_price": 8.8},
        {"trade_date": date(2024, 1, 5), "close_price": 9.7},
        {"trade_date": date(2024, 1, 8), "close_price": 10.6},
        {"trade_date": date(2024, 1, 9), "close_price": 9.8},
        {"trade_date": date(2024, 1, 10), "close_price": 8.9},
        {"trade_date": date(2024, 1, 11), "close_price": 9.9},
        {"trade_date": date(2024, 1, 12), "close_price": 10.9},
    ]


def test_zigzag_detector_marks_major_turning_points() -> None:
    from swinginsight.domain.turning_points.zigzag import ZigZagDetector

    detector = ZigZagDetector(reversal_pct=0.08)

    points = detector.detect(sample_price_series())

    assert [point.point_type for point in points] == ["trough", "peak", "trough", "peak"]
    assert [point.point_date for point in points] == [
        date(2024, 1, 4),
        date(2024, 1, 8),
        date(2024, 1, 10),
        date(2024, 1, 12),
    ]


def test_volatility_filter_drops_small_reversals() -> None:
    from swinginsight.domain.turning_points.filters import filter_by_min_separation_pct
    from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint

    points = [
        DetectedTurningPoint(point_date=date(2024, 1, 4), point_type="trough", point_price=8.8, confirm_date=date(2024, 1, 5)),
        DetectedTurningPoint(point_date=date(2024, 1, 8), point_type="peak", point_price=10.6, confirm_date=date(2024, 1, 9)),
        DetectedTurningPoint(point_date=date(2024, 1, 10), point_type="trough", point_price=10.2, confirm_date=date(2024, 1, 11)),
    ]

    filtered = filter_by_min_separation_pct(points, min_separation_pct=0.05)

    assert [point.point_type for point in filtered] == ["trough", "peak"]
