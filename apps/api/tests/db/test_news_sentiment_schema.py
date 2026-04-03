from datetime import UTC, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, inspect, select, func
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    return inspect(engine), Session


def test_news_sentiment_tables_exist() -> None:
    inspector, _ = build_session()

    table_names = set(inspector.get_table_names())

    assert "news_sentiment_result" in table_names
    assert "news_event_result" in table_names


def test_news_event_result_allows_multiple_events_per_news() -> None:
    from swinginsight.db.models.news import NewsEventResult, NewsRaw

    _, Session = build_session()

    with Session() as session:
        session.add(
            NewsRaw(
                news_uid="demo:1",
                stock_code="000001",
                title="公司发布业绩预增公告，同时控股股东拟减持",
                summary=None,
                content=None,
                publish_time=datetime(2026, 4, 2, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=datetime(2026, 4, 2, 9, 0, tzinfo=UTC).date(),
                source_name="demo",
                source_type="announcement",
            )
        )
        session.commit()
        news = session.scalar(select(NewsRaw).where(NewsRaw.news_uid == "demo:1"))
        assert news is not None

        session.add_all(
            [
                NewsEventResult(
                    news_id=news.id,
                    stock_code="000001",
                    sentence_index=0,
                    sentence_text="公司发布业绩预增公告",
                    event_type="earnings",
                    event_polarity="positive",
                    event_strength=4,
                    entity_main="000001",
                    model_version="rules:v1",
                ),
                NewsEventResult(
                    news_id=news.id,
                    stock_code="000001",
                    sentence_index=1,
                    sentence_text="控股股东拟减持",
                    event_type="capital_action",
                    event_polarity="negative",
                    event_strength=3,
                    entity_main="000001",
                    model_version="rules:v1",
                ),
            ]
        )
        session.commit()

        assert session.scalar(
            select(func.count()).select_from(NewsEventResult).where(NewsEventResult.news_id == news.id)
        ) == 2
