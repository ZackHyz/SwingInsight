from datetime import date
from pathlib import Path
import sys

from alembic import command
from alembic.config import Config
import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_daily_price_unique_constraint() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.market_data import DailyPrice

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)

    with Session() as session:
        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 2),
                open_price=10,
                high_price=11,
                low_price=9,
                close_price=10.5,
                adj_type="qfq",
            )
        )
        session.commit()

        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 2),
                open_price=10,
                high_price=11,
                low_price=9,
                close_price=10.5,
                adj_type="qfq",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_segment_uid_length_supports_algorithm_version_suffix() -> None:
    from swinginsight.db.models.segment import SwingSegment

    assert SwingSegment.__table__.c.segment_uid.type.length >= 128


def test_alembic_upgrade_from_0009_creates_watchlist_refresh_task_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    database_path = tmp_path / "watchlist-upgrade.db"
    database_url = f"sqlite:///{database_path}"
    alembic_cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    monkeypatch.setenv("DATABASE_URL", database_url)

    command.upgrade(alembic_cfg, "0009_market_scan_result")
    engine = create_engine(database_url, future=True)
    with engine.connect() as connection:
        assert "watchlist_refresh_task" not in inspect(connection).get_table_names()

    command.upgrade(alembic_cfg, "head")
    with engine.connect() as connection:
        inspector = inspect(connection)
        assert "market_scan_result" in inspector.get_table_names()
        assert "watchlist_refresh_task" in inspector.get_table_names()
        indexes = {index["name"] for index in inspector.get_indexes("market_scan_result")}
        assert "ix_market_scan_result_scan_date_rank_no" in indexes
        assert "ix_market_scan_result_stock_code_scan_date" in indexes
        unique_constraints = {item["name"] for item in inspector.get_unique_constraints("market_scan_result")}
        assert "uq_market_scan_result_scan_date_stock_code" in unique_constraints
        columns = {item["name"] for item in inspector.get_columns("market_scan_result")}
        assert {"scan_date", "stock_code", "rank_no", "rank_score", "pattern_score", "confidence"} <= columns
        count = connection.execute(text("SELECT COUNT(*) FROM market_scan_result")).scalar_one()
        assert count == 0
        watchlist_indexes = {index["name"] for index in inspector.get_indexes("watchlist_refresh_task")}
        assert "ix_watchlist_refresh_task_status_start_time" in watchlist_indexes
        watchlist_columns = {item["name"] for item in inspector.get_columns("watchlist_refresh_task")}
        assert {"scope_key", "status", "scan_date", "row_count"} <= watchlist_columns
