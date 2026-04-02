from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
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
        ("import", date(2026, 3, 26), date(2026, 4, 2)),
        ("process", date(2026, 3, 26), date(2026, 4, 2)),
        ("align", date(2026, 3, 26), date(2026, 4, 2)),
    ]
