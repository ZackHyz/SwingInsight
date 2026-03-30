from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.api.routes.news import get_segment_news_payload
from swinginsight.db.models.segment import SegmentLabel, SwingSegment


def get_segment_detail_payload(session: Session, segment_id: int) -> dict[str, object] | None:
    segment = session.scalar(select(SwingSegment).where(SwingSegment.id == segment_id))
    if segment is None:
        return None

    labels = session.scalars(select(SegmentLabel).where(SegmentLabel.segment_id == segment_id)).all()
    return {
        "segment": {
            "id": segment.id,
            "stock_code": segment.stock_code,
            "trend_direction": segment.trend_direction,
            "start_date": segment.start_date.isoformat(),
            "end_date": segment.end_date.isoformat(),
            "start_price": float(segment.start_price),
            "end_price": float(segment.end_price),
            "pct_change": float(segment.pct_change) if segment.pct_change is not None else None,
            "duration_days": segment.duration_days,
            "max_drawdown_pct": float(segment.max_drawdown_pct) if segment.max_drawdown_pct is not None else None,
            "max_upside_pct": float(segment.max_upside_pct) if segment.max_upside_pct is not None else None,
            "avg_daily_change_pct": float(segment.avg_daily_change_pct) if segment.avg_daily_change_pct is not None else None,
        },
        "news_timeline": get_segment_news_payload(session, segment_id),
        "labels": [
            {
                "label_type": label.label_type,
                "label_name": label.label_name,
                "label_value": label.label_value,
            }
            for label in labels
        ],
    }
