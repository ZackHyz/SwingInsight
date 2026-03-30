from __future__ import annotations

from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint


def filter_by_min_separation_pct(
    points: list[DetectedTurningPoint], min_separation_pct: float
) -> list[DetectedTurningPoint]:
    if min_separation_pct <= 0 or len(points) < 2:
        return points

    filtered: list[DetectedTurningPoint] = [points[0]]
    for point in points[1:]:
        previous = filtered[-1]
        move_pct = abs(point.point_price - previous.point_price) / previous.point_price
        if move_pct >= min_separation_pct:
            filtered.append(point)
    return filtered
