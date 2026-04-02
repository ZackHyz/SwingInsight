from __future__ import annotations

from collections.abc import Sequence
from statistics import median

from swinginsight.domain.turning_points.filters import filter_by_min_separation_pct
from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint, ZigZagDetector


def calibrate_turning_point_params(
    *,
    price_series: list[dict[str, object]],
    manual_points: Sequence[DetectedTurningPoint],
    default_reversal_pct: float,
    default_min_separation_pct: float,
) -> tuple[float, float]:
    if len(manual_points) < 3:
        return default_reversal_pct, default_min_separation_pct

    reversals = [
        abs(current.point_price - previous.point_price) / previous.point_price
        for previous, current in zip(manual_points, manual_points[1:], strict=False)
        if previous.point_price > 0
    ]
    if not reversals:
        return default_reversal_pct, default_min_separation_pct

    candidate_reversals = _build_reversal_candidates(reversals, default_reversal_pct)
    candidate_min_separations = _build_min_separation_candidates(reversals, default_min_separation_pct)
    manual_keys = {(point.point_date, point.point_type) for point in manual_points}

    best_pair = (default_reversal_pct, default_min_separation_pct)
    best_score = float("-inf")

    for reversal_pct in candidate_reversals:
        detector = ZigZagDetector(reversal_pct=reversal_pct)
        detected_points = detector.detect(price_series)
        for min_separation_pct in candidate_min_separations:
            points = filter_by_min_separation_pct(detected_points, min_separation_pct=min_separation_pct)
            score = _score_detection(points=points, manual_keys=manual_keys, default_pair=(default_reversal_pct, default_min_separation_pct), pair=(reversal_pct, min_separation_pct))
            if score > best_score:
                best_score = score
                best_pair = (reversal_pct, min_separation_pct)

    return best_pair


def _build_reversal_candidates(reversals: Sequence[float], default_reversal_pct: float) -> list[float]:
    base = median(reversals)
    values = {
        default_reversal_pct,
        _clamp(base * 0.45, 0.02, 0.18),
        _clamp(base * 0.60, 0.02, 0.18),
        _clamp(base * 0.75, 0.02, 0.18),
        _clamp(base * 0.90, 0.02, 0.18),
        _clamp(base, 0.02, 0.18),
    }
    return sorted(values)


def _build_min_separation_candidates(reversals: Sequence[float], default_min_separation_pct: float) -> list[float]:
    floor = min(reversals)
    values = {
        default_min_separation_pct,
        _clamp(floor * 0.20, 0.01, 0.12),
        _clamp(floor * 0.30, 0.01, 0.12),
        _clamp(floor * 0.40, 0.01, 0.12),
        _clamp(floor * 0.50, 0.01, 0.12),
    }
    return sorted(values)


def _score_detection(
    *,
    points: Sequence[DetectedTurningPoint],
    manual_keys: set[tuple[object, object]],
    default_pair: tuple[float, float],
    pair: tuple[float, float],
) -> float:
    detected_keys = {(point.point_date, point.point_type) for point in points}
    matches = len(manual_keys & detected_keys)
    missing = len(manual_keys - detected_keys)
    extras = len(detected_keys - manual_keys)
    distance_penalty = abs(pair[0] - default_pair[0]) + abs(pair[1] - default_pair[1])
    return matches * 5.0 - missing * 3.0 - extras * 1.25 - distance_penalty


def _clamp(value: float, lower: float, upper: float) -> float:
    return max(lower, min(upper, round(value, 4)))
