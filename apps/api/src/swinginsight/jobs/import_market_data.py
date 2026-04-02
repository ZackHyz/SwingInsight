from __future__ import annotations

from datetime import date
import os

from swinginsight.db.base import Base
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed
from swinginsight.ingest.adapters.demo_daily_price_feed import DemoDailyPriceFeed
from swinginsight.ingest.daily_price_importer import DailyPriceImporter, ImportResult
from swinginsight.ingest.source_priority import parse_priority
from sqlalchemy import select


def build_daily_price_feed(*, demo: bool) -> tuple[object, str]:
    if demo:
        return DemoDailyPriceFeed(), "demo"

    priorities = parse_priority(os.getenv("DATA_SOURCE_PRIORITY_DAILY_PRICE"), ["akshare"])
    for source_name in priorities:
        if source_name == "akshare":
            return AkshareDailyPriceFeed(), "akshare"
        if source_name == "demo":
            return DemoDailyPriceFeed(), "demo"
    raise ValueError("No supported daily price source configured")


def ensure_stock_basic(session, stock_code: str, feed: object) -> None:
    fetch_metadata = getattr(feed, "fetch_stock_metadata", None)
    if fetch_metadata is None:
        existing = session.scalar(select(StockBasic).where(StockBasic.stock_code == stock_code))
        if existing is None:
            session.add(
                StockBasic(
                    stock_code=stock_code,
                    stock_name=stock_code,
                    market="A",
                    industry=None,
                    concept_tags=[],
                )
            )
        return

    metadata = fetch_metadata(stock_code)
    existing = session.scalar(select(StockBasic).where(StockBasic.stock_code == stock_code))
    if existing is None:
        session.add(StockBasic(**metadata))
        return
    existing.stock_name = metadata.get("stock_name", existing.stock_name)
    existing.market = metadata.get("market", existing.market)
    existing.industry = metadata.get("industry", existing.industry)
    existing.concept_tags = metadata.get("concept_tags", existing.concept_tags)


def import_daily_prices(stock_code: str, start: date | None = None, end: date | None = None, demo: bool = False) -> ImportResult:
    Base.metadata.create_all(get_engine())
    feed, source_name = build_daily_price_feed(demo=demo)
    with session_scope() as session:
        ensure_stock_basic(session, stock_code, feed)
        importer = DailyPriceImporter(session=session, feed=feed, source_name=source_name)
        return importer.run(stock_code=stock_code, start=start, end=end)
