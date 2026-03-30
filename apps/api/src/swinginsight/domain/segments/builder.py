from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from swinginsight.domain.segments.metrics import compute_segment_metrics
from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint


@dataclass(slots=True, frozen=True)
class BuiltSegment:
    segment_uid: str
    stock_code: str
    start_date: object
    end_date: object
    start_point_type: str
    end_point_type: str
    start_price: float
    end_price: float
    pct_change: float | None
    duration_days: int | None
    max_drawdown_pct: float | None
    max_rebound_pct: float | None
    max_upside_pct: float | None
    avg_daily_change_pct: float | None
    trend_direction: str
    segment_type: str
    source_version: str


def build_segments(
    *,
    stock_code: str,
    turning_points: list[DetectedTurningPoint],
    version_code: str,
    price_window_lookup: dict[tuple[object, object], list[dict[str, object]]] | None = None,
) -> list[BuiltSegment]:
    if len(turning_points) < 2:
        return []

    segments: list[BuiltSegment] = []
    for start, end in pairwise(turning_points):
        metrics = compute_segment_metrics(
            start=start,
            end=end,
            price_window=(price_window_lookup or {}).get((start.point_date, end.point_date), []),
        )
        trend_direction = "up" if end.point_price >= start.point_price else "down"
        segments.append(
            BuiltSegment(
                segment_uid=f"{stock_code}:{start.point_date.isoformat()}:{end.point_date.isoformat()}:{version_code}",
                stock_code=stock_code,
                start_date=start.point_date,
                end_date=end.point_date,
                start_point_type=start.point_type,
                end_point_type=end.point_type,
                start_price=round(start.point_price, 4),
                end_price=round(end.point_price, 4),
                pct_change=metrics["pct_change"],
                duration_days=int(metrics["duration_days"]),
                max_drawdown_pct=metrics["max_drawdown_pct"],
                max_rebound_pct=metrics["max_rebound_pct"],
                max_upside_pct=metrics["max_upside_pct"],
                avg_daily_change_pct=metrics["avg_daily_change_pct"],
                trend_direction=trend_direction,
                segment_type=f"{trend_direction}_swing",
                source_version=version_code,
            )
        )

    return segments


def pairwise(points: list[DetectedTurningPoint]) -> Iterable[tuple[DetectedTurningPoint, DetectedTurningPoint]]:
    for index in range(len(points) - 1):
        yield points[index], points[index + 1]
