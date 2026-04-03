from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import (
    NewsEventResult,
    NewsProcessed,
    NewsRaw,
    NewsSentimentResult,
    PointNewsMap,
    SegmentNewsMap,
)
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.services.news_sentiment_service import (
    adjust_sentiment_with_position,
    resolve_base_sentiment_score,
    resolve_heat_score,
)


def build_current_news_summary(session: Session, stock_code: str, anchor_date: date, lookback_days: int = 5) -> dict[str, float]:
    window_start = anchor_date - timedelta(days=lookback_days)
    current_segment = session.scalar(
        select(SwingSegment)
        .where(SwingSegment.stock_code == stock_code, SwingSegment.is_final.is_(True), SwingSegment.end_date <= anchor_date)
        .order_by(SwingSegment.end_date.desc(), SwingSegment.id.desc())
        .limit(1)
    )
    current_point = session.scalar(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True), TurningPoint.point_date <= anchor_date)
        .order_by(TurningPoint.point_date.desc(), TurningPoint.id.desc())
        .limit(1)
    )
    rows = session.execute(
        select(NewsRaw, NewsProcessed, NewsSentimentResult)
        .outerjoin(NewsProcessed, NewsProcessed.news_id == NewsRaw.id)
        .outerjoin(NewsSentimentResult, NewsSentimentResult.news_id == NewsRaw.id)
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
            "avg_adjusted_sentiment": 0.0,
            "positive_event_count": 0.0,
            "negative_event_count": 0.0,
        }

    news_ids = [raw.id for raw, _, _ in rows]
    segment_mappings = _load_segment_mappings(session, current_segment=current_segment, news_ids=news_ids)
    point_mappings = _load_point_mappings(session, current_point=current_point, news_ids=news_ids)
    event_rows = session.execute(
        select(NewsEventResult.news_id, NewsEventResult.event_type, NewsEventResult.event_polarity)
        .where(NewsEventResult.news_id.in_(news_ids))
        .order_by(NewsEventResult.news_id.asc(), NewsEventResult.sentence_index.asc(), NewsEventResult.event_type.asc())
    ).all()
    event_types_by_news: dict[int, list[str]] = {}
    positive_event_count = 0
    negative_event_count = 0
    for news_id, event_type, event_polarity in event_rows:
        event_types = event_types_by_news.setdefault(news_id, [])
        if event_type not in event_types:
            event_types.append(event_type)
        if event_polarity == "positive":
            positive_event_count += 1
        elif event_polarity == "negative":
            negative_event_count += 1

    total = len(rows)
    announcement_count = sum(
        1 for _, processed, _ in rows if processed is not None and processed.category == "announcement"
    )
    positive_count = sum(
        1
        for raw, processed, sentiment_result in rows
        if _resolve_sentiment_label(raw=raw, processed=processed, sentiment_result=sentiment_result) == "positive"
    )
    high_heat_count = sum(1 for _, processed, _ in rows if processed is not None and processed.heat_level == "high")
    adjusted_scores = [
        adjust_sentiment_with_position(
            base_score=resolve_base_sentiment_score(
                sentiment_result.sentiment_score_base if sentiment_result is not None else None,
                _resolve_sentiment_label(raw=raw, processed=processed, sentiment_result=sentiment_result),
            ),
            category=processed.category if processed is not None else raw.source_type,
            relation_type=_resolve_relation_type(
                segment_mapping=segment_mappings.get(raw.id),
                point_mapping=point_mappings.get(raw.id),
            ),
            point_type=point_mappings.get(raw.id).point_type if point_mappings.get(raw.id) is not None else None,
            heat_score=resolve_heat_score(
                sentiment_result.heat_score if sentiment_result is not None else None,
                processed.heat_level if processed is not None else None,
            ),
            event_types=event_types_by_news.get(raw.id, []),
        )
        for raw, processed, sentiment_result in rows
    ]

    return {
        "window_news_count": float(total),
        "announcement_count": float(announcement_count),
        "positive_news_ratio": positive_count / total,
        "high_heat_count": float(high_heat_count),
        "avg_adjusted_sentiment": round(sum(adjusted_scores) / len(adjusted_scores), 4) if adjusted_scores else 0.0,
        "positive_event_count": float(positive_event_count),
        "negative_event_count": float(negative_event_count),
    }


def _load_segment_mappings(
    session: Session,
    *,
    current_segment: SwingSegment | None,
    news_ids: list[int],
) -> dict[int, SegmentNewsMap]:
    if current_segment is None or not news_ids:
        return {}
    mappings = session.scalars(
        select(SegmentNewsMap).where(
            SegmentNewsMap.segment_id == current_segment.id,
            SegmentNewsMap.news_id.in_(news_ids),
        )
    ).all()
    return {mapping.news_id: mapping for mapping in mappings}


def _load_point_mappings(
    session: Session,
    *,
    current_point: TurningPoint | None,
    news_ids: list[int],
) -> dict[int, PointNewsMap]:
    if current_point is None or not news_ids:
        return {}
    mappings = session.scalars(
        select(PointNewsMap).where(
            PointNewsMap.point_id == current_point.id,
            PointNewsMap.news_id.in_(news_ids),
        )
    ).all()
    return {mapping.news_id: mapping for mapping in mappings}


def _resolve_relation_type(
    *,
    segment_mapping: SegmentNewsMap | None,
    point_mapping: PointNewsMap | None,
) -> str | None:
    if segment_mapping is not None and segment_mapping.relation_type != "inside_segment":
        return segment_mapping.relation_type
    if point_mapping is not None:
        return point_mapping.relation_type
    if segment_mapping is not None:
        return segment_mapping.relation_type
    return None


def _resolve_sentiment_label(
    *,
    raw: NewsRaw,
    processed: NewsProcessed | None,
    sentiment_result: NewsSentimentResult | None,
) -> str | None:
    if sentiment_result is not None and sentiment_result.sentiment_label is not None:
        return sentiment_result.sentiment_label
    if processed is not None and processed.sentiment is not None:
        return processed.sentiment
    return raw.sentiment
