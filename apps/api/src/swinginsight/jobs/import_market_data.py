from __future__ import annotations

from datetime import date

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.adapters.demo_daily_price_feed import DemoDailyPriceFeed
from swinginsight.ingest.daily_price_importer import DailyPriceImporter, ImportResult


def import_daily_prices(stock_code: str, start: date | None = None, end: date | None = None, demo: bool = False) -> ImportResult:
    Base.metadata.create_all(get_engine())
    feed = DemoDailyPriceFeed() if demo else DemoDailyPriceFeed()
    with session_scope() as session:
        importer = DailyPriceImporter(session=session, feed=feed, source_name="demo" if demo else "demo")
        return importer.run(stock_code=stock_code, start=start, end=end)
