from __future__ import annotations

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.pattern_feature_service import PatternFeatureMaterializeResult, PatternFeatureService


def materialize_pattern_features(*, stock_code: str, feature_sets: list[str] | None = None) -> PatternFeatureMaterializeResult:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        return PatternFeatureService(session).materialize(stock_code=stock_code, feature_sets=feature_sets)
