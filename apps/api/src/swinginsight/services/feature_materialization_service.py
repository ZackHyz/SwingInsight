from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.news import NewsEventResult, NewsProcessed, NewsRaw, NewsSentimentResult, SegmentNewsMap
from swinginsight.db.models.segment import SegmentFeature, SegmentLabel, SwingSegment
from swinginsight.domain.features.news import NewsFeatureItem, compute_news_features
from swinginsight.domain.features.technical import compute_technical_features
from swinginsight.domain.labels.rules import derive_labels
from swinginsight.services.news_sentiment_service import (
    adjust_sentiment_with_position,
    resolve_base_sentiment_score,
    resolve_heat_score,
)
from swinginsight.services.segment_news_alignment_service import align_segment_news


FEATURE_VERSION = "feature:v1"


@dataclass(slots=True, frozen=True)
class MaterializationResult:
    features: list[SegmentFeature]
    labels: list[SegmentLabel]

def materialize_segment_features(session: Session, segment_id: int) -> list[SegmentFeature]:
    segment = session.scalar(select(SwingSegment).where(SwingSegment.id == segment_id))
    if segment is None:
        raise ValueError(f"segment not found: {segment_id}")

    price_rows = session.scalars(
        select(DailyPrice)
        .where(
            DailyPrice.stock_code == segment.stock_code,
            DailyPrice.trade_date >= segment.start_date,
            DailyPrice.trade_date <= segment.end_date,
        )
        .order_by(DailyPrice.trade_date.asc())
    ).all()

    existing_news_maps = session.scalars(select(SegmentNewsMap).where(SegmentNewsMap.segment_id == segment_id)).all()
    if not existing_news_maps:
        align_segment_news(session, segment_id=segment_id, before_days=5, after_days=5)

    news_rows = session.execute(
        select(
            SegmentNewsMap.news_id,
            SegmentNewsMap.relation_type,
            NewsRaw.sentiment,
            NewsRaw.is_duplicate,
            NewsProcessed.category,
            NewsProcessed.heat_level,
            NewsProcessed.sub_category,
            NewsSentimentResult.sentiment_label,
            NewsSentimentResult.sentiment_score_base,
            NewsSentimentResult.heat_score,
            NewsSentimentResult.event_conflict_flag,
        )
        .join(NewsRaw, NewsRaw.id == SegmentNewsMap.news_id)
        .outerjoin(NewsProcessed, NewsProcessed.news_id == NewsRaw.id)
        .outerjoin(NewsSentimentResult, NewsSentimentResult.news_id == NewsRaw.id)
        .where(SegmentNewsMap.segment_id == segment_id)
    ).all()
    news_ids = [news_id for news_id, *_ in news_rows]
    event_rows = session.execute(
        select(NewsEventResult.news_id, NewsEventResult.event_type)
        .where(NewsEventResult.news_id.in_(news_ids))
        .order_by(NewsEventResult.news_id.asc(), NewsEventResult.sentence_index.asc(), NewsEventResult.event_type.asc())
    ).all() if news_ids else []
    event_types_by_news: dict[int, list[str]] = {}
    for news_id, event_type in event_rows:
        event_types = event_types_by_news.setdefault(news_id, [])
        if event_type not in event_types:
            event_types.append(event_type)
    news_items = [
        NewsFeatureItem(
            relation_type=relation_type,
            sentiment=sentiment_label or sentiment,
            is_duplicate=bool(is_duplicate),
            category=category,
            heat_level=heat_level,
            sub_category=sub_category,
            sentiment_score_adjusted=adjust_sentiment_with_position(
                base_score=resolve_base_sentiment_score(sentiment_score_base, sentiment_label or sentiment),
                category=category,
                relation_type=relation_type,
                point_type="trough" if relation_type == "before_trough" else "peak" if relation_type == "after_peak" else None,
                heat_score=resolve_heat_score(heat_score, heat_level),
                event_types=event_types_by_news.get(news_id, []),
            ),
            event_conflict_flag=bool(event_conflict_flag),
            event_types=event_types_by_news.get(news_id, []),
        )
        for (
            news_id,
            relation_type,
            sentiment,
            is_duplicate,
            category,
            heat_level,
            sub_category,
            sentiment_label,
            sentiment_score_base,
            heat_score,
            event_conflict_flag,
        ) in news_rows
    ]

    technical = compute_technical_features(segment, price_rows)
    news = compute_news_features(news_items)

    session.execute(
        delete(SegmentFeature).where(
            SegmentFeature.segment_id == segment_id,
            SegmentFeature.version_code == FEATURE_VERSION,
        )
    )
    session.execute(
        delete(SegmentLabel).where(
            SegmentLabel.segment_id == segment_id,
            SegmentLabel.version_code == FEATURE_VERSION,
        )
    )

    features: list[SegmentFeature] = []
    for feature_name, value in {**technical, **news}.items():
        feature = SegmentFeature(
            segment_id=segment_id,
            stock_code=segment.stock_code,
            feature_group="technical" if feature_name in technical else "news",
            feature_name=feature_name,
            feature_value_num=float(value),
            version_code=FEATURE_VERSION,
        )
        session.add(feature)
        features.append(feature)

    labels: list[SegmentLabel] = []
    for label_name, score in derive_labels(technical=technical, news=news):
        label = SegmentLabel(
            segment_id=segment_id,
            stock_code=segment.stock_code,
            label_type="pattern",
            label_name=label_name,
            label_value="matched",
            score=score,
            source_type="system",
            version_code=FEATURE_VERSION,
        )
        session.add(label)
        labels.append(label)

    session.flush()
    return features


def get_segment_library_rows(session: Session) -> list[dict[str, object]]:
    segments = session.scalars(
        select(SwingSegment).where(SwingSegment.is_final.is_(True)).order_by(SwingSegment.id.asc())
    ).all()
    rows: list[dict[str, object]] = []
    for segment in segments:
        labels = session.scalars(select(SegmentLabel).where(SegmentLabel.segment_id == segment.id)).all()
        rows.append(
            {
                "id": segment.id,
                "stock_code": segment.stock_code,
                "segment_type": segment.segment_type,
                "label_names": [label.label_name for label in labels],
                "pct_change": float(segment.pct_change) if segment.pct_change is not None else None,
                "duration_days": segment.duration_days,
            }
        )
    return rows
