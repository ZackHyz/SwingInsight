from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.base import Base
from swinginsight.db.models.market_data import TaskRunLog
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.point_news_alignment_service import align_point_news
from swinginsight.services.segment_news_alignment_service import align_segment_news


@dataclass(slots=True, frozen=True)
class AlignNewsResult:
    point_mappings: int
    segment_mappings: int


def align_news(
    stock_code: str,
    start: date | None = None,
    end: date | None = None,
    *,
    session: Session | None = None,
) -> AlignNewsResult:
    started_at = datetime.now(UTC)

    def run(current_session: Session) -> AlignNewsResult:
        point_query = select(TurningPoint).where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
        if start is not None:
            point_query = point_query.where(TurningPoint.point_date >= start)
        if end is not None:
            point_query = point_query.where(TurningPoint.point_date <= end)
        points = current_session.scalars(point_query.order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())).all()

        segment_query = select(SwingSegment).where(
            SwingSegment.stock_code == stock_code,
            SwingSegment.is_final.is_(True),
        )
        if start is not None:
            segment_query = segment_query.where(SwingSegment.end_date >= start)
        if end is not None:
            segment_query = segment_query.where(SwingSegment.start_date <= end)
        segments = current_session.scalars(segment_query.order_by(SwingSegment.start_date.asc(), SwingSegment.id.asc())).all()

        point_mappings = 0
        segment_mappings = 0
        for point in points:
            point_mappings += len(align_point_news(current_session, point.id))
        for segment in segments:
            segment_mappings += len(align_segment_news(current_session, segment.id))
        finished_at = datetime.now(UTC)
        current_session.add(
            TaskRunLog(
                task_name=f"align-news:{stock_code}",
                task_type="align_news",
                target_code=stock_code,
                status="success",
                start_time=started_at,
                end_time=finished_at,
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                input_params_json={
                    "stock_code": stock_code,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                },
                result_summary=f"point_mappings={point_mappings},segment_mappings={segment_mappings}",
            )
        )
        current_session.commit()
        return AlignNewsResult(point_mappings=point_mappings, segment_mappings=segment_mappings)

    if session is not None:
        return run(session)

    Base.metadata.create_all(get_engine())
    with session_scope() as current_session:
        return run(current_session)
