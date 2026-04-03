from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


class FakeDailyPriceFeed:
    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        return [
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 2),
                "open_price": 10,
                "high_price": 11,
                "low_price": 9,
                "close_price": 10.5,
                "adj_type": "qfq",
                "data_source": "fake",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 3),
                "open_price": 10.5,
                "high_price": 11.5,
                "low_price": 10,
                "close_price": 11,
                "adj_type": "qfq",
                "data_source": "fake",
            },
        ]


class FakeDailyPriceFeedUpdated(FakeDailyPriceFeed):
    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        rows = super().fetch_daily_prices(stock_code, start, end)
        rows[0]["close_price"] = 10.8
        return rows


def build_session():
    from swinginsight.db.base import Base

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def test_daily_price_importer_upserts_rows() -> None:
    from swinginsight.db.models.market_data import DailyPrice, TaskRunLog
    from swinginsight.ingest.daily_price_importer import DailyPriceImporter

    session = build_session()
    importer = DailyPriceImporter(session=session, feed=FakeDailyPriceFeed())

    result = importer.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert result.inserted == 2
    assert result.updated == 0

    rows = session.scalars(select(DailyPrice).order_by(DailyPrice.trade_date)).all()
    assert len(rows) == 2
    assert rows[0].close_price == 10.5

    log = session.scalars(select(TaskRunLog)).one()
    assert log.task_type == "import_daily_price"
    assert log.status == "success"

    updater = DailyPriceImporter(session=session, feed=FakeDailyPriceFeedUpdated())
    update_result = updater.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert update_result.inserted == 0
    assert update_result.updated == 1
    assert update_result.skipped == 1
    updated_row = session.scalars(
        select(DailyPrice).where(DailyPrice.stock_code == "000001", DailyPrice.trade_date == date(2024, 1, 2))
    ).one()
    assert updated_row.close_price == 10.8


def test_daily_price_importer_uses_resolved_source_name_for_task_log_and_payloads() -> None:
    from swinginsight.db.models.market_data import DailyPrice, TaskRunLog
    from swinginsight.ingest.daily_price_importer import DailyPriceImporter

    class PriorityDailyPriceFeed:
        resolved_source_name = "tushare"

        def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
            return [
                {
                    "stock_code": stock_code,
                    "trade_date": date(2024, 1, 2),
                    "open_price": 10,
                    "high_price": 11,
                    "low_price": 9,
                    "close_price": 10.5,
                    "adj_type": "qfq",
                    "data_source": "akshare",
                }
            ]

    session = build_session()
    importer = DailyPriceImporter(session=session, feed=PriorityDailyPriceFeed(), source_name="priority")

    result = importer.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert result.inserted == 1

    row = session.scalars(select(DailyPrice)).one()
    assert row.data_source == "tushare"

    log = session.scalars(select(TaskRunLog)).one()
    assert log.input_params_json["source"] == "tushare"


def test_daily_price_importer_ignores_row_level_data_source_when_source_is_resolved() -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.ingest.daily_price_importer import DailyPriceImporter

    class PriorityDailyPriceFeed:
        resolved_source_name = "tushare"

        def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
            return [
                {
                    "stock_code": stock_code,
                    "trade_date": date(2024, 1, 2),
                    "open_price": 10,
                    "high_price": 11,
                    "low_price": 9,
                    "close_price": 10.5,
                    "adj_type": "qfq",
                    "data_source": "mootdx",
                }
            ]

    session = build_session()
    importer = DailyPriceImporter(session=session, feed=PriorityDailyPriceFeed(), source_name="priority")

    result = importer.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert result.inserted == 1

    row = session.scalars(select(DailyPrice)).one()
    assert row.data_source == "tushare"
