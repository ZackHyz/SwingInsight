from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
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


def seed_daily_prices(session, stock_code: str, start: date, closes: list[float]) -> None:
    from swinginsight.db.models.market_data import DailyPrice

    for index, close in enumerate(closes):
        trade_date = start + timedelta(days=index)
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
    session.commit()


def test_score_validation_service_logs_pattern_score_requests() -> None:
    from swinginsight.services.score_validation_service import ScoreValidationService

    session = build_session()
    service = ScoreValidationService(session)

    row = service.log_pattern_score(
        stock_code="600157",
        query_window_id=123,
        query_end_date=date(2026, 4, 1),
        predicted_win_rate=0.67,
        predicted_avg_return=0.043,
        sample_count=12,
    )
    session.commit()

    assert row.id > 0
    assert row.stock_code == "600157"
    assert row.query_window_id == 123
    assert float(row.predicted_win_rate) == 0.67
    assert float(row.predicted_avg_return) == 0.043
    assert row.sample_count == 12
    assert row.actual_return_5d is None
    assert row.actual_return_10d is None


def test_score_validation_service_backfills_actual_returns() -> None:
    from swinginsight.services.score_validation_service import ScoreValidationService

    session = build_session()
    seed_daily_prices(
        session,
        "600157",
        date(2026, 4, 1),
        [10.0, 10.2, 10.3, 10.1, 10.0, 10.5, 10.7, 10.8, 10.9, 11.0, 11.2, 11.1],
    )

    service = ScoreValidationService(session)
    service.log_pattern_score(
        stock_code="600157",
        query_window_id=200,
        query_end_date=date(2026, 4, 1),
        predicted_win_rate=0.6,
        predicted_avg_return=0.02,
        sample_count=8,
    )
    session.commit()

    updated = service.backfill_actual_returns(stock_code="600157")
    session.commit()

    assert updated == 1
    report = service.build_validation_report(stock_code="600157")
    assert report["evaluated_samples_5d"] == 1
    assert report["evaluated_samples_10d"] == 1
    assert report["brier_score_10d"] >= 0.0
    assert report["brier_score_10d"] <= 1.0


def test_score_validation_service_reports_brier_and_bin_error() -> None:
    from swinginsight.services.score_validation_service import ScoreValidationService

    session = build_session()
    service = ScoreValidationService(session)
    seed_daily_prices(
        session,
        "600157",
        date(2026, 1, 1),
        [10.0, 10.1, 10.2, 10.3, 10.4, 10.6, 10.7, 10.8, 10.7, 10.6, 10.5, 10.4, 10.3],
    )
    seed_daily_prices(
        session,
        "600157",
        date(2026, 2, 1),
        [10.0, 9.9, 9.8, 9.7, 9.6, 9.4, 9.2, 9.1, 9.0, 8.9, 8.8, 8.7, 8.6],
    )

    service.log_pattern_score(
        stock_code="600157",
        query_window_id=1,
        query_end_date=date(2026, 1, 1),
        predicted_win_rate=0.7,
        predicted_avg_return=0.03,
        sample_count=10,
    )
    service.log_pattern_score(
        stock_code="600157",
        query_window_id=2,
        query_end_date=date(2026, 2, 1),
        predicted_win_rate=0.3,
        predicted_avg_return=-0.02,
        sample_count=10,
    )
    session.commit()

    service.backfill_actual_returns(stock_code="600157")
    session.commit()
    report = service.build_validation_report(stock_code="600157")

    assert report["evaluated_samples_10d"] == 2
    assert report["brier_score_10d"] < 0.25
    assert len(report["win_rate_bin_error_10d"]) == 3
