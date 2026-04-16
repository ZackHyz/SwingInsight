from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.api.routes.predictions import load_latest_prediction_summary
from swinginsight.db.models.market_data import DailyPrice, TradeRecord
from swinginsight.db.models.news import (
    NewsEventResult,
    NewsProcessed,
    NewsRaw,
    NewsSentimentResult,
    PointNewsMap,
    SegmentNewsMap,
)
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import TurningPoint


@dataclass(slots=True, frozen=True)
class StockResearchNewsRow:
    raw: NewsRaw
    processed: NewsProcessed | None
    sentiment_result: NewsSentimentResult | None
    segment_mapping: SegmentNewsMap | None
    point_mapping: PointNewsMap | None
    event_metadata: dict[str, object]


@dataclass(slots=True, frozen=True)
class StockResearchSnapshot:
    stock: StockBasic
    prices: list[DailyPrice]
    auto_points: list[TurningPoint]
    provisional_points: list[TurningPoint]
    final_points: list[TurningPoint]
    trade_markers: list[TradeRecord]
    news_rows: list[StockResearchNewsRow]
    prediction: dict[str, object] | None


def load_stock_research_snapshot(session: Session, stock_code: str) -> StockResearchSnapshot | None:
    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == stock_code))
    if stock is None:
        return None

    prices = session.scalars(
        select(DailyPrice).where(DailyPrice.stock_code == stock_code).order_by(DailyPrice.trade_date.asc())
    ).all()
    auto_points = session.scalars(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.source_type == "system")
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    final_points = session.scalars(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    provisional_points = session.scalars(
        select(TurningPoint)
        .where(
            TurningPoint.stock_code == stock_code,
            TurningPoint.source_type == "system",
            TurningPoint.is_final.is_(False),
        )
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    current_segment = session.scalar(
        select(SwingSegment)
        .where(SwingSegment.stock_code == stock_code, SwingSegment.is_final.is_(True))
        .order_by(SwingSegment.end_date.desc(), SwingSegment.id.desc())
        .limit(1)
    )
    current_point = final_points[-1] if final_points else None
    trade_markers = session.scalars(
        select(TradeRecord)
        .where(TradeRecord.stock_code == stock_code)
        .order_by(TradeRecord.trade_date.asc(), TradeRecord.id.asc())
    ).all()
    raw_news_rows = session.execute(
        select(NewsRaw, NewsProcessed, NewsSentimentResult)
        .outerjoin(NewsProcessed, NewsProcessed.news_id == NewsRaw.id)
        .outerjoin(NewsSentimentResult, NewsSentimentResult.news_id == NewsRaw.id)
        .where(NewsRaw.stock_code == stock_code)
        .order_by(NewsRaw.news_date.desc(), NewsRaw.id.desc())
        .limit(12)
    ).all()
    news_ids = [raw.id for raw, _, _ in raw_news_rows]
    current_segment_mappings = _load_segment_news_mappings(
        session,
        current_segment=current_segment,
        news_ids=news_ids,
    )
    current_point_mappings = _load_point_news_mappings(
        session,
        current_point=current_point,
        news_ids=news_ids,
    )
    event_metadata_by_news = _load_event_metadata(session, news_ids=news_ids)
    prediction = load_latest_prediction_summary(session, stock_code)

    news_rows = [
        StockResearchNewsRow(
            raw=raw,
            processed=processed,
            sentiment_result=sentiment_result,
            segment_mapping=current_segment_mappings.get(raw.id),
            point_mapping=current_point_mappings.get(raw.id),
            event_metadata=event_metadata_by_news.get(raw.id, _default_event_metadata()),
        )
        for raw, processed, sentiment_result in raw_news_rows
    ]
    return StockResearchSnapshot(
        stock=stock,
        prices=prices,
        auto_points=auto_points,
        provisional_points=provisional_points,
        final_points=final_points,
        trade_markers=trade_markers,
        news_rows=news_rows,
        prediction=prediction,
    )


def _load_segment_news_mappings(
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


def _load_point_news_mappings(
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


def _load_event_metadata(session: Session, *, news_ids: list[int]) -> dict[int, dict[str, object]]:
    if not news_ids:
        return {}
    rows = session.execute(
        select(NewsEventResult.news_id, NewsEventResult.event_type, NewsEventResult.event_polarity)
        .where(NewsEventResult.news_id.in_(news_ids))
        .order_by(
            NewsEventResult.news_id.asc(),
            NewsEventResult.sentence_index.asc(),
            NewsEventResult.event_type.asc(),
        )
    ).all()
    event_metadata_by_news: dict[int, dict[str, object]] = {}
    for news_id, event_type, event_polarity in rows:
        metadata = event_metadata_by_news.setdefault(news_id, _default_event_metadata())
        event_types = metadata["event_types"]
        if event_type not in event_types:
            event_types.append(event_type)
        if event_polarity == "positive":
            metadata["positive_event_count"] += 1
        elif event_polarity == "negative":
            metadata["negative_event_count"] += 1
    return event_metadata_by_news


def _default_event_metadata() -> dict[str, object]:
    return {
        "event_types": [],
        "positive_event_count": 0,
        "negative_event_count": 0,
    }
