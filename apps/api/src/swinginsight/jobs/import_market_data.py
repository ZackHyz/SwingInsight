from __future__ import annotations

from datetime import date

from swinginsight.db.base import Base
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed
from swinginsight.ingest.adapters.demo_daily_price_feed import DemoDailyPriceFeed
from swinginsight.ingest.adapters.mootdx_daily_price_feed import MootdxDailyPriceFeed
from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed
from swinginsight.ingest.daily_price_importer import DailyPriceImporter, ImportResult
from swinginsight.ingest.ports import DailyPriceFeed
from swinginsight.settings import Settings
from sqlalchemy import select


class PriorityDailyPriceFeed:
    def __init__(self, providers: list[tuple[str, DailyPriceFeed]]) -> None:
        self.providers = providers
        self.provider_names = [provider_name for provider_name, _ in providers]
        self.resolved_source_name: str | None = None

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        errors: list[str] = []
        for provider_name, provider in self.providers:
            try:
                payloads = provider.fetch_daily_prices(stock_code=stock_code, start=start, end=end)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{provider_name}: {exc}")
                continue
            if payloads:
                self.resolved_source_name = provider_name
                return payloads
            errors.append(f"{provider_name}: no daily prices returned")

        self.resolved_source_name = None
        raise RuntimeError("All daily price providers failed: " + "; ".join(errors))

    def fetch_stock_metadata(self, stock_code: str):
        for provider_name, provider in self.providers:
            fetch_metadata = getattr(provider, "fetch_stock_metadata", None)
            if fetch_metadata is None:
                continue
            try:
                metadata = fetch_metadata(stock_code)
            except Exception as exc:  # noqa: BLE001
                continue
            if metadata is not None:
                return metadata
        return None


def build_daily_price_feed(*, demo: bool, settings: Settings | None = None) -> tuple[DailyPriceFeed, str]:
    if demo:
        return DemoDailyPriceFeed(), "demo"

    resolved_settings = settings or Settings.model_validate({})
    providers: list[tuple[str, DailyPriceFeed]] = []
    for source_name in resolved_settings.data_source_priority_daily_price:
        provider = _build_daily_price_provider(source_name, resolved_settings)
        if provider is not None:
            providers.append((source_name, provider))

    if not providers:
        raise ValueError("No supported daily price source configured")
    return PriorityDailyPriceFeed(providers), "priority"


def _build_daily_price_provider(source_name: str, settings: Settings) -> DailyPriceFeed | None:
    if source_name == "akshare":
        return AkshareDailyPriceFeed()
    if source_name == "tushare":
        return TushareDailyPriceFeed(token=settings.tushare_token)
    if source_name == "mootdx":
        return MootdxDailyPriceFeed()
    if source_name == "demo":
        return DemoDailyPriceFeed()
    return None


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
    if metadata is None:
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
