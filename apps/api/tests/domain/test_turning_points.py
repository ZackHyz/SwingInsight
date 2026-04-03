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
    assert points[-1].confirm_date is None


def test_zigzag_detector_uses_kline_highs_and_lows_for_turning_points() -> None:
    from swinginsight.domain.turning_points.zigzag import ZigZagDetector

    detector = ZigZagDetector(reversal_pct=0.08)
    price_series = [
        {"trade_date": date(2024, 1, 2), "close_price": 10.0, "high_price": 10.2, "low_price": 9.8},
        {"trade_date": date(2024, 1, 3), "close_price": 9.95, "high_price": 11.0, "low_price": 9.9},
        {"trade_date": date(2024, 1, 4), "close_price": 9.96, "high_price": 10.0, "low_price": 9.0},
        {"trade_date": date(2024, 1, 5), "close_price": 9.97, "high_price": 10.9, "low_price": 9.95},
        {"trade_date": date(2024, 1, 8), "close_price": 10.0, "high_price": 10.1, "low_price": 9.7},
    ]

    points = detector.detect(price_series)

    assert [(point.point_date, point.point_type, point.point_price) for point in points[:3]] == [
        (date(2024, 1, 3), "peak", 11.0),
        (date(2024, 1, 4), "trough", 9.0),
        (date(2024, 1, 5), "peak", 10.9),
    ]


def test_zigzag_detector_moves_last_peak_forward_when_later_bar_breaks_higher() -> None:
    from swinginsight.domain.turning_points.zigzag import ZigZagDetector

    detector = ZigZagDetector(reversal_pct=0.08)
    price_series = [
        {"trade_date": date(2026, 3, 27), "close_price": 2.55, "high_price": 2.56, "low_price": 2.46},
        {"trade_date": date(2026, 3, 30), "close_price": 2.56, "high_price": 2.57, "low_price": 2.49},
        {"trade_date": date(2026, 3, 31), "close_price": 2.51, "high_price": 2.58, "low_price": 2.50},
        {"trade_date": date(2026, 4, 1), "close_price": 2.63, "high_price": 2.68, "low_price": 2.51},
        {"trade_date": date(2026, 4, 2), "close_price": 2.62, "high_price": 2.67, "low_price": 2.57},
        {"trade_date": date(2026, 4, 3), "close_price": 2.70, "high_price": 2.75, "low_price": 2.60},
    ]

    points = detector.detect(price_series)

    assert points[-1].point_type == "peak"
    assert points[-1].point_date == date(2026, 4, 3)
    assert points[-1].point_price == 2.75
    assert points[-1].confirm_date is None


def test_zigzag_detector_moves_last_trough_forward_when_later_bar_breaks_lower() -> None:
    from swinginsight.domain.turning_points.zigzag import ZigZagDetector

    detector = ZigZagDetector(reversal_pct=0.08)
    price_series = [
        {"trade_date": date(2026, 3, 27), "close_price": 2.86, "high_price": 2.90, "low_price": 2.80},
        {"trade_date": date(2026, 3, 30), "close_price": 2.84, "high_price": 2.88, "low_price": 2.79},
        {"trade_date": date(2026, 3, 31), "close_price": 2.87, "high_price": 2.91, "low_price": 2.82},
        {"trade_date": date(2026, 4, 1), "close_price": 2.70, "high_price": 2.72, "low_price": 2.60},
        {"trade_date": date(2026, 4, 2), "close_price": 2.69, "high_price": 2.71, "low_price": 2.61},
        {"trade_date": date(2026, 4, 3), "close_price": 2.63, "high_price": 2.66, "low_price": 2.52},
    ]

    points = detector.detect(price_series)

    assert points[-1].point_type == "trough"
    assert points[-1].point_date == date(2026, 4, 3)
    assert points[-1].point_price == 2.52
    assert points[-1].confirm_date is None


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


def test_calibration_learns_thresholds_from_manual_points() -> None:
    from swinginsight.domain.turning_points.calibration import calibrate_turning_point_params
    from swinginsight.domain.turning_points.filters import filter_by_min_separation_pct
    from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint, ZigZagDetector

    price_series = [
        {"trade_date": date(2024, 2, 1), "close_price": 10.0},
        {"trade_date": date(2024, 2, 2), "close_price": 9.7},
        {"trade_date": date(2024, 2, 5), "close_price": 9.4},
        {"trade_date": date(2024, 2, 6), "close_price": 9.8},
        {"trade_date": date(2024, 2, 7), "close_price": 9.3},
        {"trade_date": date(2024, 2, 8), "close_price": 9.6},
        {"trade_date": date(2024, 2, 9), "close_price": 9.1},
        {"trade_date": date(2024, 2, 19), "close_price": 9.7},
    ]
    manual_points = [
        DetectedTurningPoint(point_date=date(2024, 2, 5), point_type="trough", point_price=9.4),
        DetectedTurningPoint(point_date=date(2024, 2, 6), point_type="peak", point_price=9.8),
        DetectedTurningPoint(point_date=date(2024, 2, 7), point_type="trough", point_price=9.3),
        DetectedTurningPoint(point_date=date(2024, 2, 8), point_type="peak", point_price=9.6),
        DetectedTurningPoint(point_date=date(2024, 2, 9), point_type="trough", point_price=9.1),
        DetectedTurningPoint(point_date=date(2024, 2, 19), point_type="peak", point_price=9.7),
    ]

    reversal_pct, min_separation_pct = calibrate_turning_point_params(
        price_series=price_series,
        manual_points=manual_points,
        default_reversal_pct=0.08,
        default_min_separation_pct=0.05,
    )

    assert reversal_pct < 0.08

    detected = filter_by_min_separation_pct(ZigZagDetector(reversal_pct=reversal_pct).detect(price_series), min_separation_pct)

    assert [(point.point_date, point.point_type) for point in detected] == [
        (date(2024, 2, 5), "trough"),
        (date(2024, 2, 6), "peak"),
        (date(2024, 2, 7), "trough"),
        (date(2024, 2, 8), "peak"),
        (date(2024, 2, 9), "trough"),
        (date(2024, 2, 19), "peak"),
    ]
