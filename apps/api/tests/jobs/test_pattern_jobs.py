from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sqlite3
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def seed_job_fixture(db_path: Path) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from swinginsight.db.base import Base
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.segment import SwingSegment

    engine = create_engine(f"sqlite+pysqlite:///{db_path}", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)

    with Session() as session:
        previous_close = 10.0
        closes = [10.0, 10.2, 10.1, 10.3, 10.5, 10.7, 10.9, 11.0, 11.2, 11.1, 11.4, 11.6]
        for index, close_price in enumerate(closes):
            trade_date = date(2024, 1, 1) + timedelta(days=index)
            session.add(
                DailyPrice(
                    stock_code="000001",
                    trade_date=trade_date,
                    open_price=previous_close,
                    high_price=max(previous_close, close_price) + 0.2,
                    low_price=min(previous_close, close_price) - 0.2,
                    close_price=close_price,
                    pre_close_price=previous_close,
                    volume=1_000_000 + index * 10_000,
                    turnover_rate=2.0 + index * 0.1,
                    adj_type="qfq",
                    data_source="test",
                )
            )
            previous_close = close_price

        session.add(
            SwingSegment(
                segment_uid="seg-job-000001-20240103-20240109",
                stock_code="000001",
                start_date=date(2024, 1, 3),
                end_date=date(2024, 1, 9),
                start_point_type="trough",
                end_point_type="peak",
                start_price=10.0,
                end_price=11.0,
                pct_change=10.0,
                duration_days=6,
                segment_type="up_swing",
                trend_direction="up",
                source_version="test",
                is_final=True,
            )
        )
        session.commit()


def test_build_pattern_windows_job_persists_rows(tmp_path, monkeypatch) -> None:
    from swinginsight.db.session import get_engine, get_session_factory
    from swinginsight.jobs.build_pattern_windows import build_pattern_windows

    db_path = tmp_path / "pattern-jobs.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{db_path}")
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    seed_job_fixture(db_path)

    result = build_pattern_windows(stock_code="000001")

    assert result.created == 6

    connection = sqlite3.connect(db_path)
    try:
        row = connection.execute("select count(*) from pattern_window").fetchone()
        assert row[0] == 6
    finally:
        connection.close()
