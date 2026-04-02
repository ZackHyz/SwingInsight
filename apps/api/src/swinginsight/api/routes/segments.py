from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.api.routes.news import get_segment_news_payload
from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.segment import SegmentLabel, SwingSegment
from swinginsight.db.models.turning_point import TurningPoint


SEGMENT_CHART_CONTEXT_TRADING_DAYS = 10


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


def get_segment_chart_payload(session: Session, segment_id: int) -> dict[str, object] | None:
    segment = session.scalar(select(SwingSegment).where(SwingSegment.id == segment_id))
    if segment is None:
        return None

    price_rows = session.scalars(
        select(DailyPrice).where(DailyPrice.stock_code == segment.stock_code).order_by(DailyPrice.trade_date.asc())
    ).all()
    if not price_rows:
        return {
            "segment": {
                "id": segment.id,
                "stock_code": segment.stock_code,
                "start_date": segment.start_date.isoformat(),
                "end_date": segment.end_date.isoformat(),
            },
            "highlight_range": {
                "start_date": segment.start_date.isoformat(),
                "end_date": segment.end_date.isoformat(),
            },
            "prices": [],
            "auto_turning_points": [],
            "final_turning_points": [],
        }

    start_index = _find_first_trade_index_on_or_after(price_rows, segment.start_date)
    end_index = _find_last_trade_index_on_or_before(price_rows, segment.end_date)
    window_start_index = max(start_index - SEGMENT_CHART_CONTEXT_TRADING_DAYS, 0)
    window_end_index = min(end_index + SEGMENT_CHART_CONTEXT_TRADING_DAYS + 1, len(price_rows))
    window_rows = price_rows[window_start_index:window_end_index]
    window_start_date = window_rows[0].trade_date
    window_end_date = window_rows[-1].trade_date

    auto_points = session.scalars(
        select(TurningPoint)
        .where(
            TurningPoint.stock_code == segment.stock_code,
            TurningPoint.source_type == "system",
            TurningPoint.point_date >= window_start_date,
            TurningPoint.point_date <= window_end_date,
        )
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    final_points = session.scalars(
        select(TurningPoint)
        .where(
            TurningPoint.stock_code == segment.stock_code,
            TurningPoint.is_final.is_(True),
            TurningPoint.point_date >= window_start_date,
            TurningPoint.point_date <= window_end_date,
        )
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()

    return {
        "segment": {
            "id": segment.id,
            "stock_code": segment.stock_code,
            "start_date": segment.start_date.isoformat(),
            "end_date": segment.end_date.isoformat(),
        },
        "highlight_range": {
            "start_date": segment.start_date.isoformat(),
            "end_date": segment.end_date.isoformat(),
        },
        "prices": [_serialize_price_row(row) for row in window_rows],
        "auto_turning_points": [_serialize_turning_point(row) for row in auto_points],
        "final_turning_points": [_serialize_turning_point(row) for row in final_points],
    }


def _find_first_trade_index_on_or_after(rows: list[DailyPrice], target_date) -> int:
    for index, row in enumerate(rows):
        if row.trade_date >= target_date:
            return index
    return len(rows) - 1


def _find_last_trade_index_on_or_before(rows: list[DailyPrice], target_date) -> int:
    for index in range(len(rows) - 1, -1, -1):
        if rows[index].trade_date <= target_date:
            return index
    return 0


def _serialize_price_row(row: DailyPrice) -> dict[str, object]:
    return {
        "trade_date": row.trade_date.isoformat(),
        "open_price": float(row.open_price),
        "high_price": float(row.high_price),
        "low_price": float(row.low_price),
        "close_price": float(row.close_price),
        "volume": int(row.volume) if row.volume is not None else None,
    }


def _serialize_turning_point(row: TurningPoint) -> dict[str, object]:
    return {
        "id": row.id,
        "point_date": row.point_date.isoformat(),
        "point_type": row.point_type,
        "point_price": float(row.point_price),
        "source_type": row.source_type,
    }
