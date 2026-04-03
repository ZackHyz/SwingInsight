from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_prices(session, *, stock_code: str, start_date: date, closes: list[float]) -> None:
    from swinginsight.db.models.market_data import DailyPrice

    previous_close = closes[0]
    for index, close_price in enumerate(closes):
        trade_date = start_date + timedelta(days=index)
        open_price = previous_close
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=trade_date,
                open_price=open_price,
                high_price=max(open_price, close_price) + 0.2,
                low_price=min(open_price, close_price) - 0.2,
                close_price=close_price,
                pre_close_price=previous_close,
                change_pct=((close_price / previous_close) - 1.0) * 100 if previous_close else None,
                volume=1_000_000 + index * 10_000,
                turnover_rate=2.0 + index * 0.1,
                adj_type="qfq",
                data_source="test",
            )
        )
        previous_close = close_price
    session.commit()


def seed_segment(
    session,
    *,
    stock_code: str,
    start_date: date,
    end_date: date,
) -> int:
    from swinginsight.db.models.segment import SwingSegment

    segment = SwingSegment(
        segment_uid=f"seg-{stock_code}-{start_date.isoformat()}-{end_date.isoformat()}",
        stock_code=stock_code,
        start_date=start_date,
        end_date=end_date,
        start_point_type="trough",
        end_point_type="peak",
        start_price=10.0,
        end_price=11.0,
        pct_change=10.0,
        duration_days=(end_date - start_date).days,
        segment_type="up_swing",
        trend_direction="up",
        source_version="test",
        is_final=True,
    )
    session.add(segment)
    session.commit()
    return segment.id


def test_build_pattern_windows_creates_fixed_7_bar_windows_with_segment_mapping() -> None:
    from swinginsight.db.models.pattern import PatternWindow
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    seed_prices(
        session,
        stock_code="000001",
        start_date=date(2024, 1, 1),
        closes=[10.0, 10.2, 10.1, 10.3, 10.5, 10.7, 10.9, 11.0, 11.2, 11.1],
    )
    segment_id = seed_segment(
        session,
        stock_code="000001",
        start_date=date(2024, 1, 3),
        end_date=date(2024, 1, 9),
    )

    result = PatternWindowService(session).build_windows(stock_code="000001", window_size=7)

    assert result.created == 4
    sample = session.scalar(select(PatternWindow).where(PatternWindow.segment_id == segment_id))
    assert sample is not None
    assert sample.window_size == 7


def test_materialize_pattern_future_stats_persists_forward_returns() -> None:
    from swinginsight.db.models.pattern import PatternFutureStat, PatternWindow
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    seed_prices(
        session,
        stock_code="000001",
        start_date=date(2024, 1, 1),
        closes=[10.0, 10.1, 10.3, 10.5, 10.6, 10.7, 10.8, 11.0, 10.9, 11.3, 11.4, 11.2, 11.6, 11.7, 11.8, 11.9, 12.0],
    )

    window = PatternWindow(
        window_uid="pw-future-000001-20240101-20240107",
        stock_code="000001",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 7),
        window_size=7,
        start_close=10.0,
        end_close=10.8,
        period_pct_change=8.0,
        highest_day_pos=6,
        lowest_day_pos=0,
        trend_label="uptrend",
        feature_version="pattern:v1",
    )
    session.add(window)
    session.commit()

    result = PatternWindowService(session).materialize_future_stats(stock_code="000001")

    stats = session.scalar(select(PatternFutureStat).where(PatternFutureStat.window_id == window.id))
    assert result.updated == 1
    assert stats is not None
    assert round(float(stats.ret_1d or 0), 4) == 0.0185
    assert round(float(stats.ret_10d or 0), 4) == 0.1111
