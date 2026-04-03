from __future__ import annotations

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.pattern_window_service import PatternBuildResult, PatternWindowService


def build_pattern_windows(*, stock_code: str, window_size: int = 7) -> PatternBuildResult:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        return PatternWindowService(session).build_windows(stock_code=stock_code, window_size=window_size)
