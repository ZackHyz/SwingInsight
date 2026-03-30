from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice, TaskRunLog
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.domain.segments.builder import build_segments
from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint


@dataclass(slots=True, frozen=True)
class SegmentGenerationResult:
    inserted: int


class SegmentGenerationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rebuild_segments(self, *, stock_code: str, version_code: str) -> SegmentGenerationResult:
        points = self.session.scalars(
            select(TurningPoint)
            .where(
                TurningPoint.stock_code == stock_code,
                TurningPoint.is_final.is_(True),
                TurningPoint.version_code == version_code,
            )
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()

        detected_points = [
            DetectedTurningPoint(
                point_date=point.point_date,
                point_type=point.point_type,
                point_price=float(point.point_price),
                confirm_date=point.confirm_date,
            )
            for point in points
        ]

        lookup: dict[tuple[object, object], list[dict[str, object]]] = {}
        for start, end in zip(points, points[1:], strict=False):
            price_rows = self.session.scalars(
                select(DailyPrice)
                .where(
                    DailyPrice.stock_code == stock_code,
                    DailyPrice.trade_date >= start.point_date,
                    DailyPrice.trade_date <= end.point_date,
                )
                .order_by(DailyPrice.trade_date.asc())
            ).all()
            lookup[(start.point_date, end.point_date)] = [
                {
                    "trade_date": row.trade_date,
                    "high_price": float(row.high_price),
                    "low_price": float(row.low_price),
                    "close_price": float(row.close_price),
                }
                for row in price_rows
            ]

        built_segments = build_segments(
            stock_code=stock_code,
            turning_points=detected_points,
            version_code=version_code,
            price_window_lookup=lookup,
        )

        self.session.execute(
            delete(SwingSegment).where(
                SwingSegment.stock_code == stock_code,
                SwingSegment.source_version == version_code,
                SwingSegment.is_final.is_(True),
            )
        )

        point_ids_by_date_type = {(point.point_date, point.point_type): point.id for point in points}
        for segment in built_segments:
            self.session.add(
                SwingSegment(
                    segment_uid=segment.segment_uid,
                    stock_code=segment.stock_code,
                    start_point_id=point_ids_by_date_type.get((segment.start_date, segment.start_point_type)),
                    end_point_id=point_ids_by_date_type.get((segment.end_date, segment.end_point_type)),
                    start_date=segment.start_date,
                    end_date=segment.end_date,
                    start_point_type=segment.start_point_type,
                    end_point_type=segment.end_point_type,
                    start_price=segment.start_price,
                    end_price=segment.end_price,
                    pct_change=segment.pct_change,
                    duration_days=segment.duration_days,
                    max_drawdown_pct=segment.max_drawdown_pct,
                    max_rebound_pct=segment.max_rebound_pct,
                    max_upside_pct=segment.max_upside_pct,
                    avg_daily_change_pct=segment.avg_daily_change_pct,
                    segment_type=segment.segment_type,
                    trend_direction=segment.trend_direction,
                    source_version=segment.source_version,
                    is_final=True,
                )
            )

        self.session.add(
            TaskRunLog(
                task_name="rebuild_segments",
                task_type="segment_generation",
                target_code=stock_code,
                status="success",
                start_time=datetime.now(UTC).replace(tzinfo=None),
                end_time=datetime.now(UTC).replace(tzinfo=None),
                input_params_json={"version_code": version_code},
                result_summary=f"inserted={len(built_segments)}",
            )
        )
        self.session.flush()
        return SegmentGenerationResult(inserted=len(built_segments))
