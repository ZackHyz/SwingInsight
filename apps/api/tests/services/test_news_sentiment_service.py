from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_news(session):
    from swinginsight.db.models.news import NewsRaw

    session.add(
        NewsRaw(
            news_uid="sentiment-1",
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


def test_process_news_writes_sentiment_and_event_results() -> None:
    from swinginsight.db.models.news import NewsEventResult, NewsSentimentResult
    from swinginsight.services.news_processing_service import NewsProcessingService

    session = build_session()
    seed_news(session)

    result = NewsProcessingService(session).process_batch([1])

    sentiment = session.scalar(select(NewsSentimentResult).where(NewsSentimentResult.news_id == 1))
    events = session.scalars(
        select(NewsEventResult).where(NewsEventResult.news_id == 1).order_by(NewsEventResult.sentence_index.asc())
    ).all()

    assert result.processed_count == 1
    assert result.sentiment_results == 1
    assert result.event_results == 2
    assert sentiment is not None
    assert sentiment.event_conflict_flag is True
    assert sentiment.sentiment_label == "neutral"
    assert len(events) == 2


def test_process_news_updates_existing_sentiment_rows_instead_of_duplicating() -> None:
    from swinginsight.db.models.news import NewsEventResult, NewsSentimentResult
    from swinginsight.services.news_processing_service import NewsProcessingService

    session = build_session()
    seed_news(session)

    service = NewsProcessingService(session)
    service.process_batch([1])
    service.process_batch([1])

    assert session.scalar(select(func.count()).select_from(NewsSentimentResult).where(NewsSentimentResult.news_id == 1)) == 1
    assert session.scalar(select(func.count()).select_from(NewsEventResult).where(NewsEventResult.news_id == 1)) == 2
