from __future__ import annotations

from datetime import UTC, date, datetime
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


def seed_pending_news(session) -> None:
    from swinginsight.db.models.news import NewsRaw

    session.add(
        NewsRaw(
            news_uid="job-news-1",
            stock_code="000001",
            title="公司发布业绩预增公告，同时控股股东拟减持",
            summary="业绩向好但出现资本动作分歧",
            content=None,
            publish_time=datetime(2026, 4, 2, 9, 0, tzinfo=UTC).replace(tzinfo=None),
            news_date=date(2026, 4, 2),
            source_name="cninfo",
            source_type="announcement",
            url="https://example.com/news/1",
            data_source="fake",
            fetch_time=datetime(2026, 4, 2, 9, 5, tzinfo=UTC).replace(tzinfo=None),
            is_parsed=False,
            parse_status="pending",
        )
    )
    session.commit()


def test_process_news_job_reports_sentiment_and_event_counts() -> None:
    from swinginsight.jobs.process_news import process_news

    session = build_session()
    seed_pending_news(session)

    result = process_news(stock_code="000001", start=date(2026, 4, 1), end=date(2026, 4, 2), session=session)

    assert result.processed_count == 1
    assert result.sentiment_results == 1
    assert result.event_results == 2
    assert result.conflict_news == 1
