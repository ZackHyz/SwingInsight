from __future__ import annotations

from contextlib import contextmanager
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
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)(), engine


def test_import_news_defaults_to_recent_seven_day_window(monkeypatch) -> None:
    from swinginsight.jobs import import_news as import_news_job

    session, engine = build_session()
    calls: list[tuple[str, date | None, date | None]] = []

    class FixedDate(date):
        @classmethod
        def today(cls) -> "FixedDate":
            return cls(2026, 4, 2)

    class CapturingFeed:
        def fetch_news(self, stock_code: str, start: date | None, end: date | None):
            calls.append((stock_code, start, end))
            return []

    @contextmanager
    def fake_session_scope():
        yield session

    monkeypatch.setattr(import_news_job, "date", FixedDate)
    monkeypatch.setattr(import_news_job, "get_engine", lambda: engine)
    monkeypatch.setattr(import_news_job, "session_scope", fake_session_scope)
    monkeypatch.setattr(import_news_job, "build_news_feeds", lambda demo, source_list: [(CapturingFeed(), "capture")])

    inserted = import_news_job.import_news(stock_code="000001")

    assert inserted == 0
    assert calls == [("000001", FixedDate(2026, 3, 26), FixedDate(2026, 4, 2))]
