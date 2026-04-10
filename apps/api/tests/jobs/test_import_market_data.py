from __future__ import annotations

from contextlib import contextmanager
from datetime import date
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
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)(), engine


class FailingDailyPriceFeed:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[str, date | None, date | None]] = []

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        self.calls.append((stock_code, start, end))
        raise RuntimeError(f"{self.name} unavailable")


class WorkingDailyPriceFeed:
    def __init__(self, name: str) -> None:
        self.name = name
        self.calls: list[tuple[str, date | None, date | None]] = []

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        self.calls.append((stock_code, start, end))
        return [
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 2),
                "open_price": 10.0,
                "high_price": 11.0,
                "low_price": 9.5,
                "close_price": 10.5,
                "adj_type": "qfq",
                "data_source": self.name,
            }
        ]


def test_build_daily_price_feed_uses_default_priority_order():
    from swinginsight.jobs.import_market_data import build_daily_price_feed
    from swinginsight.settings import Settings

    settings = Settings.model_validate({})

    feed, source_name = build_daily_price_feed(demo=False, settings=settings)

    assert source_name == "priority"
    assert feed.provider_names == ["akshare", "tushare", "mootdx"]


def test_build_metadata_feeds_uses_metadata_priority_independently():
    from swinginsight.jobs.import_market_data import build_metadata_feeds
    from swinginsight.settings import Settings

    settings = Settings.model_validate(
        {
            "data_source_priority_daily_price": ["mootdx"],
            "data_source_priority_metadata": ["tushare", "akshare", "mootdx"],
        }
    )

    feeds = build_metadata_feeds(settings=settings)

    assert [source_name for source_name, _ in feeds] == ["tushare", "akshare"]


def test_import_daily_prices_uses_provider_chain_and_reports_fallback_source(monkeypatch):
    from swinginsight.jobs import import_market_data as import_market_data_job

    session, engine = build_session()
    akshare_feed = FailingDailyPriceFeed("akshare")
    tushare_feed = WorkingDailyPriceFeed("tushare")
    mootdx_feed = FailingDailyPriceFeed("mootdx")

    class PriorityFeed:
        provider_names = ["akshare", "tushare", "mootdx"]
        resolved_source_name = None

        def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
            for feed in (akshare_feed, tushare_feed, mootdx_feed):
                try:
                    rows = feed.fetch_daily_prices(stock_code=stock_code, start=start, end=end)
                except RuntimeError:
                    continue
                self.resolved_source_name = feed.name
                return rows
            raise RuntimeError("all providers failed")

    @contextmanager
    def fake_session_scope():
        yield session

    monkeypatch.setattr(import_market_data_job, "build_daily_price_feed", lambda *, demo, settings=None: (PriorityFeed(), "priority"))
    monkeypatch.setattr(import_market_data_job, "get_engine", lambda: engine)
    monkeypatch.setattr(import_market_data_job, "session_scope", fake_session_scope)

    result = import_market_data_job.import_daily_prices(
        stock_code="000001",
        start=date(2024, 1, 2),
        end=date(2024, 1, 3),
    )

    assert result.inserted == 1
    assert akshare_feed.calls == [("000001", date(2024, 1, 2), date(2024, 1, 3))]
    assert tushare_feed.calls == [("000001", date(2024, 1, 2), date(2024, 1, 3))]
    assert mootdx_feed.calls == []

    from swinginsight.db.models.market_data import DailyPrice, TaskRunLog

    row = session.scalars(select(DailyPrice)).one()
    assert row.data_source == "tushare"

    log = session.scalars(select(TaskRunLog)).one()
    assert log.input_params_json["source"] == "tushare"


def test_ensure_stock_basic_uses_metadata_priority_separately(monkeypatch):
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.jobs import import_market_data as import_market_data_job

    class FailingMetadataFeed:
        def __init__(self) -> None:
            self.stock_metadata_calls: list[str] = []

        def fetch_stock_metadata(self, stock_code: str):
            self.stock_metadata_calls.append(stock_code)
            raise RuntimeError("akshare unavailable")

    class WorkingMetadataFeed:
        def __init__(self) -> None:
            self.stock_metadata_calls: list[str] = []

        def fetch_stock_metadata(self, stock_code: str):
            self.stock_metadata_calls.append(stock_code)
            return {
                "stock_code": stock_code,
                "stock_name": "永泰能源",
                "market": "A",
                "industry": "Coal",
                "concept_tags": ["energy"],
            }

    session, _ = build_session()
    akshare_feed = FailingMetadataFeed()
    tushare_feed = WorkingMetadataFeed()

    monkeypatch.setattr(
        import_market_data_job,
        "build_metadata_feeds",
        lambda *, settings=None: [("akshare", akshare_feed), ("tushare", tushare_feed)],
    )

    import_market_data_job.ensure_stock_basic(session, "600157")

    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == "600157"))
    assert stock is not None
    assert stock.stock_name == "永泰能源"
    assert stock.market == "A"
    assert stock.industry == "Coal"
    assert stock.concept_tags == ["energy"]
    assert akshare_feed.stock_metadata_calls == ["600157"]
    assert tushare_feed.stock_metadata_calls == ["600157"]


def test_ensure_stock_basic_falls_back_to_minimal_record_when_all_metadata_providers_fail(monkeypatch):
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.jobs import import_market_data as import_market_data_job

    class FailingMetadataFeed:
        def fetch_stock_metadata(self, stock_code: str):
            raise RuntimeError(f"{stock_code} unavailable")

    session, _ = build_session()
    monkeypatch.setattr(
        import_market_data_job,
        "build_metadata_feeds",
        lambda *, settings=None: [("akshare", FailingMetadataFeed()), ("tushare", FailingMetadataFeed())],
    )

    import_market_data_job.ensure_stock_basic(session, "000001")

    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == "000001"))
    assert stock is not None
    assert stock.stock_name == "000001"
    assert stock.market == "A"
    assert stock.industry is None
    assert stock.concept_tags == []
