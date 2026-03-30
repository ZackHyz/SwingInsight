from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.news import NewsRaw, SegmentNewsMap
from swinginsight.db.models.segment import SegmentFeature, SegmentLabel, SwingSegment
from swinginsight.domain.features.news import compute_news_features
from swinginsight.domain.features.technical import compute_technical_features
from swinginsight.domain.labels.rules import derive_labels
from swinginsight.services.segment_news_alignment_service import align_segment_news


FEATURE_VERSION = "feature:v1"


@dataclass(slots=True, frozen=True)
class MaterializationResult:
    features: list[SegmentFeature]
    labels: list[SegmentLabel]


@dataclass(slots=True, frozen=True)
class NewsFeatureItem:
    relation_type: str
    sentiment: str | None
    is_duplicate: bool


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
        select(SegmentNewsMap.relation_type, NewsRaw.sentiment, NewsRaw.is_duplicate)
        .join(NewsRaw, NewsRaw.id == SegmentNewsMap.news_id)
        .where(SegmentNewsMap.segment_id == segment_id)
    ).all()
    news_items = [
        NewsFeatureItem(relation_type=relation_type, sentiment=sentiment, is_duplicate=bool(is_duplicate))
        for relation_type, sentiment, is_duplicate in news_rows
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
