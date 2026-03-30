from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select

from swinginsight.db.base import Base
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.feature_materialization_service import materialize_segment_features


@dataclass(slots=True, frozen=True)
class MaterializeFeaturesResult:
    segments: int
    features: int


def materialize_features(*, stock_code: str) -> MaterializeFeaturesResult:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        segments = session.scalars(
            select(SwingSegment).where(SwingSegment.stock_code == stock_code, SwingSegment.is_final.is_(True))
        ).all()
        feature_count = 0
        for segment in segments:
            feature_count += len(materialize_segment_features(session, segment_id=segment.id))
        return MaterializeFeaturesResult(segments=len(segments), features=feature_count)
