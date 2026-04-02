from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import NewsProcessed, NewsRaw


def build_current_news_summary(session: Session, stock_code: str, anchor_date: date, lookback_days: int = 5) -> dict[str, float]:
    window_start = anchor_date - timedelta(days=lookback_days)
    rows = session.execute(
        select(NewsRaw, NewsProcessed)
        .outerjoin(NewsProcessed, NewsProcessed.news_id == NewsRaw.id)
        .where(
            NewsRaw.stock_code == stock_code,
            NewsRaw.news_date.is_not(None),
            NewsRaw.news_date >= window_start,
            NewsRaw.news_date <= anchor_date,
        )
        .order_by(NewsRaw.news_date.asc(), NewsRaw.id.asc())
    ).all()

    if not rows:
        return {
            "window_news_count": 0.0,
            "announcement_count": 0.0,
            "positive_news_ratio": 0.0,
            "high_heat_count": 0.0,
        }

    total = len(rows)
    announcement_count = sum(1 for _, processed in rows if processed is not None and processed.category == "announcement")
    positive_count = sum(
        1 for raw, processed in rows if (processed.sentiment if processed is not None else raw.sentiment) == "positive"
    )
    high_heat_count = sum(1 for _, processed in rows if processed is not None and processed.heat_level == "high")

    return {
        "window_news_count": float(total),
        "announcement_count": float(announcement_count),
        "positive_news_ratio": positive_count / total,
        "high_heat_count": float(high_heat_count),
    }
