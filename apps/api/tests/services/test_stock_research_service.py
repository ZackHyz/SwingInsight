from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys

import sqlalchemy as sa
from sqlalchemy import create_engine, select, func, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


HELPER_PATH = Path(__file__).resolve().parents[1] / "domain" / "test_prediction_service.py"
HELPER_SPEC = importlib.util.spec_from_file_location("prediction_seed_helpers", HELPER_PATH)
assert HELPER_SPEC and HELPER_SPEC.loader
HELPER_MODULE = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPER_MODULE)
seed_prediction_context = HELPER_MODULE.seed_prediction_context


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


def test_ensure_stock_ready_refreshes_recent_news_window(monkeypatch) -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.ingest.daily_price_importer import ImportResult
    from swinginsight.jobs.align_news import AlignNewsResult
    from swinginsight.jobs.process_news import ProcessNewsResult
    from swinginsight.services import stock_research_service as stock_research_module

    session = build_session()
    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=[],
        )
    )
    session.add(
        DailyPrice(
            stock_code="000001",
            trade_date=date(2026, 4, 2),
            open_price=10.0,
            high_price=10.5,
            low_price=9.8,
            close_price=10.2,
            adj_type="qfq",
            data_source="demo",
        )
    )
    session.commit()

    calls: list[tuple[str, date | None, date | None]] = []

    def fake_import_news(stock_code: str, start: date | None = None, end: date | None = None, **_: object) -> int:
        calls.append(("import", start, end))
        return 1

    def fake_process_news(
        stock_code: str,
        start: date | None = None,
        end: date | None = None,
        **_: object,
    ) -> ProcessNewsResult:
        calls.append(("process", start, end))
        return ProcessNewsResult(processed_count=1, duplicates=0)

    def fake_align_news(
        stock_code: str,
        start: date | None = None,
        end: date | None = None,
        **_: object,
    ) -> AlignNewsResult:
        calls.append(("align", start, end))
        return AlignNewsResult(point_mappings=1, segment_mappings=1)

    monkeypatch.setattr(stock_research_module, "import_news", fake_import_news, raising=False)
    monkeypatch.setattr(stock_research_module, "process_news", fake_process_news, raising=False)
    monkeypatch.setattr(stock_research_module, "align_news", fake_align_news, raising=False)
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_live_prices",
        lambda self, stock_code, latest_trade_date: ImportResult(inserted=0, updated=0, skipped=1),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_needs_rebuild",
        lambda self, *, stock_code, latest_trade_date: False,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_rebuild_research_artifacts",
        lambda self, *, stock_code, latest_trade_date: None,
    )

    ready = stock_research_module.StockResearchService(session).ensure_stock_ready("000001")

    assert ready is True
    assert calls == [
        ("import", date(2026, 3, 19), date(2026, 4, 2)),
        ("process", date(2026, 3, 19), date(2026, 4, 2)),
        ("align", date(2026, 3, 19), date(2026, 4, 2)),
    ]


def test_ensure_stock_ready_tolerates_duplicate_price_insert_race(monkeypatch) -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.services import stock_research_service as stock_research_module

    session = build_session()
    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=[],
        )
    )
    session.add(
        DailyPrice(
            stock_code="000001",
            trade_date=date(2026, 4, 2),
            open_price=10.0,
            high_price=10.5,
            low_price=9.8,
            close_price=10.2,
            adj_type="qfq",
            data_source="demo",
        )
    )
    session.commit()

    rollback_calls = 0
    original_rollback = session.rollback

    def counting_rollback():
        nonlocal rollback_calls
        rollback_calls += 1
        return original_rollback()

    monkeypatch.setattr(session, "rollback", counting_rollback)
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_live_prices",
        lambda self, stock_code, latest_trade_date: (_ for _ in ()).throw(
            IntegrityError("duplicate", params=None, orig=Exception("duplicate"))
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_news_window",
        lambda self, stock_code, anchor_date: stock_research_module.NewsRefreshResult(
            start_date=date(2026, 3, 19),
            end_date=date(2026, 4, 2),
            inserted=0,
            processed_count=0,
            duplicates=0,
            point_mappings=0,
            segment_mappings=0,
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_needs_rebuild",
        lambda self, *, stock_code, latest_trade_date: False,
    )

    ready = stock_research_module.StockResearchService(session).ensure_stock_ready("000001")

    assert ready is True
    assert rollback_calls == 1


def test_ensure_stock_ready_retries_news_window_after_duplicate_event_race(monkeypatch) -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.ingest.daily_price_importer import ImportResult
    from swinginsight.jobs.align_news import AlignNewsResult
    from swinginsight.jobs.process_news import ProcessNewsResult
    from swinginsight.services import stock_research_service as stock_research_module

    session = build_session()
    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=[],
        )
    )
    session.add(
        DailyPrice(
            stock_code="000001",
            trade_date=date(2026, 4, 2),
            open_price=10.0,
            high_price=10.5,
            low_price=9.8,
            close_price=10.2,
            adj_type="qfq",
            data_source="demo",
        )
    )
    session.commit()

    process_calls = 0

    def fake_import_news(stock_code: str, start: date | None = None, end: date | None = None, **_: object) -> int:
        return 0

    def fake_process_news(
        stock_code: str,
        start: date | None = None,
        end: date | None = None,
        **_: object,
    ) -> ProcessNewsResult:
        nonlocal process_calls
        process_calls += 1
        if process_calls == 1:
            raise IntegrityError("duplicate", params=None, orig=Exception("duplicate"))
        return ProcessNewsResult(processed_count=1, duplicates=0)

    def fake_align_news(
        stock_code: str,
        start: date | None = None,
        end: date | None = None,
        **_: object,
    ) -> AlignNewsResult:
        return AlignNewsResult(point_mappings=1, segment_mappings=1)

    monkeypatch.setattr(stock_research_module, "import_news", fake_import_news, raising=False)
    monkeypatch.setattr(stock_research_module, "process_news", fake_process_news, raising=False)
    monkeypatch.setattr(stock_research_module, "align_news", fake_align_news, raising=False)
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_live_prices",
        lambda self, stock_code, latest_trade_date: ImportResult(inserted=0, updated=0, skipped=0),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_needs_rebuild",
        lambda self, *, stock_code, latest_trade_date: False,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_news_features",
        lambda self, *, stock_code, latest_trade_date, window_start: None,
    )

    ready = stock_research_module.StockResearchService(session).ensure_stock_ready("000001")

    assert ready is True
    assert process_calls == 2


def test_refresh_live_prices_uses_independent_metadata_priority_chain(monkeypatch) -> None:
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.jobs import import_market_data as import_market_data_job
    from swinginsight.services import stock_research_service as stock_research_module

    session = build_session()

    class PriceFeed:
        def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
            return [
                {
                    "stock_code": stock_code,
                    "trade_date": date(2026, 4, 2),
                    "open_price": 10.0,
                    "high_price": 10.5,
                    "low_price": 9.8,
                    "close_price": 10.2,
                    "adj_type": "qfq",
                    "data_source": "mootdx",
                }
            ]

    class MetadataFeed:
        def __init__(self) -> None:
            self.calls: list[str] = []

        def fetch_stock_metadata(self, stock_code: str):
            self.calls.append(stock_code)
            return {
                "stock_code": stock_code,
                "stock_name": "永泰能源",
                "market": "A",
                "industry": "Coal",
                "concept_tags": ["energy"],
            }

    metadata_feed = MetadataFeed()

    monkeypatch.setattr(stock_research_module, "build_daily_price_feed", lambda *, demo=False: (PriceFeed(), "priority"))
    monkeypatch.setattr(
        import_market_data_job,
        "build_metadata_feeds",
        lambda *, settings=None: [("tushare", metadata_feed)],
    )

    result = stock_research_module.StockResearchService(session)._refresh_live_prices(
        "600157",
        latest_trade_date=date(2026, 4, 1),
    )

    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == "600157"))
    assert result.inserted == 1
    assert stock is not None
    assert stock.stock_name == "永泰能源"
    assert stock.industry == "Coal"
    assert metadata_feed.calls == ["600157"]


def test_ensure_stock_ready_recreates_pattern_tables_and_materializes_pattern_data(monkeypatch) -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternFutureStat, PatternWindow
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.ingest.daily_price_importer import ImportResult
    from swinginsight.services import stock_research_service as stock_research_module

    session = build_session()
    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=[],
        )
    )
    seed_prediction_context(session)
    session.execute(text("drop table pattern_match_result"))
    session.execute(text("drop table pattern_feature"))
    session.execute(text("drop table pattern_future_stat"))
    session.execute(text("drop table pattern_window"))
    session.commit()

    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_live_prices",
        lambda self, stock_code, latest_trade_date: ImportResult(inserted=0, updated=0, skipped=0),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_refresh_news_window",
        lambda self, stock_code, anchor_date: stock_research_module.NewsRefreshResult(
            start_date=anchor_date,
            end_date=anchor_date,
            inserted=0,
            processed_count=0,
            duplicates=0,
            point_mappings=0,
            segment_mappings=0,
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "_needs_rebuild",
        lambda self, *, stock_code, latest_trade_date: False,
    )

    ready = stock_research_module.StockResearchService(session).ensure_stock_ready("000001")
    session.commit()

    inspector = sa.inspect(session.bind)
    assert ready is True
    assert "pattern_window" in inspector.get_table_names()
    assert session.scalar(select(func.count()).select_from(PatternWindow).where(PatternWindow.stock_code == "000001")) > 0
    assert (
        session.scalar(
            select(func.count())
            .select_from(PatternFeature)
            .join(PatternWindow, PatternWindow.id == PatternFeature.window_id)
            .where(PatternWindow.stock_code == "000001")
        )
        > 0
    )
    assert (
        session.scalar(
            select(func.count())
            .select_from(PatternFutureStat)
            .join(PatternWindow, PatternWindow.id == PatternFutureStat.window_id)
            .where(PatternWindow.stock_code == "000001")
        )
        > 0
    )
