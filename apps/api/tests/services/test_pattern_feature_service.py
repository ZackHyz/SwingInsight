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


def seed_prices(session, *, stock_code: str, start_date: date, count: int) -> None:
    from swinginsight.db.models.market_data import DailyPrice

    close_price = 10.0
    previous_close = close_price
    for index in range(count):
        close_price += 0.08 if index % 5 else -0.03
        trade_date = start_date + timedelta(days=index)
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=trade_date,
                open_price=previous_close,
                high_price=max(previous_close, close_price) + 0.15,
                low_price=min(previous_close, close_price) - 0.18,
                close_price=close_price,
                pre_close_price=previous_close,
                volume=1_000_000 + index * 5_000,
                turnover_rate=2.0 + index * 0.02,
                adj_type="qfq",
                data_source="test",
            )
        )
        previous_close = close_price
    session.commit()


def test_pattern_feature_service_materializes_feature_rows() -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternWindow
    from swinginsight.services.pattern_feature_service import PatternFeatureService

    session = build_session()
    seed_prices(session, stock_code="000001", start_date=date(2024, 1, 1), count=80)
    session.add(
        PatternWindow(
            window_uid="pw-feature-000001-20240314-20240320",
            stock_code="000001",
            start_date=date(2024, 3, 14),
            end_date=date(2024, 3, 20),
            window_size=7,
            start_close=13.0,
            end_close=13.6,
            period_pct_change=4.6,
            highest_day_pos=6,
            lowest_day_pos=0,
            trend_label="uptrend",
            feature_version="pattern:v1",
        )
    )
    session.commit()

    result = PatternFeatureService(session).materialize(stock_code="000001")

    feature_row = session.scalar(select(PatternFeature))
    assert result.windows == 1
    assert result.features == 1
    assert feature_row is not None
    assert feature_row.price_seq_json is not None


def test_pattern_feature_service_materializes_context_feature_sets() -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternWindow
    from swinginsight.services.pattern_feature_service import PatternFeatureService

    session = build_session()
    seed_prices(session, stock_code="600157", start_date=date(2024, 1, 1), count=120)
    session.add(
        PatternWindow(
            window_uid="pw-feature-600157-20240401-20240407",
            stock_code="600157",
            start_date=date(2024, 4, 1),
            end_date=date(2024, 4, 7),
            window_size=7,
            start_close=12.0,
            end_close=12.7,
            period_pct_change=5.8,
            highest_day_pos=6,
            lowest_day_pos=0,
            trend_label="uptrend",
            feature_version="pattern:v1",
        )
    )
    session.commit()

    result = PatternFeatureService(session).materialize(
        stock_code="600157",
        feature_sets=["coarse", "volume_context", "price_position", "trend_context"],
    )
    feature_row = session.scalar(select(PatternFeature))

    assert result.windows == 1
    assert result.features == 1
    assert feature_row is not None
    assert feature_row.context_feature_json is not None
    assert "vol_ratio_vs_ma20" in feature_row.context_feature_json
    assert "price_percentile_60d" in feature_row.context_feature_json
    assert "pre_trend_slope_norm" in feature_row.context_feature_json
