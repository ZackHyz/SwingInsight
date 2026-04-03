from __future__ import annotations

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.pattern_window_service import PatternFutureStatResult, PatternWindowService


def materialize_pattern_future_stats(*, stock_code: str) -> PatternFutureStatResult:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        return PatternWindowService(session).materialize_future_stats(stock_code=stock_code)
