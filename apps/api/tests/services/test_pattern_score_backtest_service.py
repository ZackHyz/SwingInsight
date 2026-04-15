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
    from swinginsight.db import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_prices(session, stock_code: str, start: date, closes: list[float]) -> None:
    from swinginsight.db.models.market_data import DailyPrice

    for offset, close in enumerate(closes):
        trade_date = start + timedelta(days=offset)
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=trade_date,
                open_price=close,
                high_price=close,
                low_price=close,
                close_price=close,
                adj_type="qfq",
                data_source="test",
            )
        )
    session.flush()


def seed_windows(session) -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternWindow

    rows = [
        ("w1", date(2024, 1, 1), date(2024, 1, 7), [0.1, 0.2, 0.3]),
        ("w2", date(2024, 1, 8), date(2024, 1, 14), [0.2, 0.3, 0.4]),
        ("w3", date(2024, 1, 15), date(2024, 1, 21), [0.9, 0.8, 0.7]),
        ("w4", date(2024, 1, 22), date(2024, 1, 28), [0.85, 0.75, 0.65]),
    ]
    for uid, start_date, end_date, vec in rows:
        window = PatternWindow(
            window_uid=f"600157:{uid}",
            stock_code="600157",
            segment_id=1,
            start_date=start_date,
            end_date=end_date,
            window_size=7,
            start_close=10.0,
            end_close=10.1,
            period_pct_change=1.0,
            highest_day_pos=6,
            lowest_day_pos=0,
            trend_label="flat",
            feature_version="pattern:v1",
        )
        session.add(window)
        session.flush()
        session.add(
            PatternFeature(
                window_id=window.id,
                coarse_vector_json=vec + [0.0] * 18,
                price_seq_json=vec,
                candle_feat_json=[0.0] * 35,
                volume_seq_json=[1.0] * 7,
                turnover_seq_json=[1.0] * 7,
                trend_context_json=[0.5],
                vola_context_json=[0.5],
                feature_version="pattern:v1",
            )
        )
    session.commit()


def test_backtest_service_uses_strict_temporal_cutoff() -> None:
    from swinginsight.db.models.prediction import BacktestResult
    from swinginsight.services.pattern_score_backtest_service import PatternScoreBacktestService

    session = build_session()
    seed_prices(session, "600157", date(2024, 1, 1), [10 + i * 0.05 for i in range(60)])
    seed_windows(session)

    result = PatternScoreBacktestService(session).run_backtest(
        stock_code="600157",
        start=date(2024, 1, 1),
        end=date(2024, 2, 20),
        horizon_days=[5, 10],
        top_k=2,
        min_reference_size=1,
    )
    session.commit()

    assert result["processed_queries"] >= 2
    rows = session.scalars(select(BacktestResult).where(BacktestResult.stock_code == "600157")).all()
    assert rows
    assert all(row.ref_latest_end_date is None or row.ref_latest_end_date < row.query_start_date for row in rows)


def test_backtest_service_builds_metrics_summary() -> None:
    from swinginsight.services.pattern_score_backtest_service import PatternScoreBacktestService

    session = build_session()
    seed_prices(
        session,
        "600157",
        date(2024, 1, 1),
        [10, 10.1, 10.3, 10.2, 10.4, 10.6, 10.7, 10.8, 10.7, 10.6, 10.5, 10.4, 10.3, 10.2, 10.1, 10.0, 9.9, 9.8, 9.7, 9.6, 9.5, 9.4, 9.3, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6, 8.5, 8.4, 8.3, 8.2, 8.1, 8.0, 7.9, 7.8, 7.7, 7.6, 7.5, 7.4, 7.3, 7.2, 7.1, 7.0, 6.9, 6.8, 6.7, 6.6, 6.5, 6.4, 6.3, 6.2, 6.1, 6.0, 5.9, 5.8, 5.7, 5.6],
    )
    seed_windows(session)

    service = PatternScoreBacktestService(session)
    service.run_backtest(
        stock_code="600157",
        start=date(2024, 1, 1),
        end=date(2024, 2, 20),
        horizon_days=[5],
        top_k=2,
        min_reference_size=1,
    )
    session.commit()

    summary = service.summarize(stock_code="600157", horizon=5, min_sample_count=1)
    assert summary["rows"] >= 1
    assert 0.0 <= summary["brier_score"] <= 1.0
    assert len(summary["tiers"]) == 3
    assert 0.0 <= summary["coverage_rate"] <= 1.0
    assert set(summary["sample_count_distribution"].keys()) == {"<5", "5-9", "10-19", "20-29", "30+"}


def test_backtest_service_applies_similarity_threshold_and_min_samples() -> None:
    from swinginsight.services.pattern_score_backtest_service import PatternScoreBacktestService

    session = build_session()
    seed_prices(session, "600157", date(2024, 1, 1), [10 + i * 0.03 for i in range(80)])
    seed_windows(session)

    result = PatternScoreBacktestService(session).run_backtest(
        stock_code="600157",
        start=date(2024, 1, 1),
        end=date(2024, 2, 20),
        horizon_days=[5],
        top_k=10,
        min_reference_size=1,
        min_similarity=0.99,
        min_samples=2,
    )
    session.commit()

    assert result["processed_queries"] >= 1
    assert result["written_rows"] == 0


def test_backtest_service_rejects_unknown_feature_names() -> None:
    import pytest

    from swinginsight.services.pattern_score_backtest_service import PatternScoreBacktestService

    session = build_session()
    seed_prices(session, "600157", date(2024, 1, 1), [10 + i * 0.03 for i in range(80)])
    seed_windows(session)

    with pytest.raises(ValueError):
        PatternScoreBacktestService(session).run_backtest(
            stock_code="600157",
            start=date(2024, 1, 1),
            end=date(2024, 2, 20),
            horizon_days=[5],
            top_k=10,
            min_reference_size=1,
            min_similarity=0.6,
            min_samples=1,
            feature_names=["not_exists_feature"],
        )
