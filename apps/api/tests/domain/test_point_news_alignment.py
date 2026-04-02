from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_point_and_news(session):
    from swinginsight.db.models.news import NewsProcessed, NewsRaw
    from swinginsight.db.models.turning_point import TurningPoint

    point = TurningPoint(
        stock_code="000001",
        point_date=date(2024, 1, 8),
        point_type="trough",
        point_price=8.8,
        source_type="manual",
        version_code="manual:latest",
        is_final=True,
    )
    session.add(point)
    session.flush()

    before_news = NewsRaw(
        stock_code="000001",
        title="利好公告提前释放",
        summary="before",
        publish_time=datetime(2024, 1, 6, 9, 0, tzinfo=UTC).replace(tzinfo=None),
        news_date=date(2024, 1, 6),
        source_name="cninfo",
        source_type="announcement",
        fetch_time=datetime(2024, 1, 6, 9, 10, tzinfo=UTC).replace(tzinfo=None),
        is_parsed=True,
        parse_status="processed",
        data_source="fake",
    )
    after_news = NewsRaw(
        stock_code="000001",
        title="利空消息冲击市场",
        summary="after",
        publish_time=datetime(2024, 1, 10, 9, 0, tzinfo=UTC).replace(tzinfo=None),
        news_date=date(2024, 1, 10),
        source_name="wire",
        source_type="media_news",
        fetch_time=datetime(2024, 1, 10, 9, 10, tzinfo=UTC).replace(tzinfo=None),
        is_parsed=True,
        parse_status="processed",
        data_source="fake",
    )
    session.add_all([before_news, after_news])
    session.flush()

    session.add_all(
        [
            NewsProcessed(
                news_id=before_news.id,
                stock_code="000001",
                clean_title="利好公告提前释放",
                category="announcement",
                sub_category="earnings",
                sentiment="positive",
                heat_level="high",
                keyword_list=["公告", "利好"],
                tag_list=["official", "first_release"],
                is_duplicate=False,
                processed_at=datetime(2024, 1, 6, 9, 10, tzinfo=UTC).replace(tzinfo=None),
            ),
            NewsProcessed(
                news_id=after_news.id,
                stock_code="000001",
                clean_title="利空消息冲击市场",
                category="media_news",
                sub_category=None,
                sentiment="negative",
                heat_level="medium",
                keyword_list=["利空"],
                tag_list=["follow_up"],
                is_duplicate=False,
                processed_at=datetime(2024, 1, 10, 9, 10, tzinfo=UTC).replace(tzinfo=None),
            ),
        ]
    )
    session.commit()
    return point


def test_align_point_news_maps_news_into_t_minus_5_to_t_plus_5() -> None:
    from swinginsight.services.point_news_alignment_service import align_point_news

    session = build_session()
    point = seed_point_and_news(session)

    rows = align_point_news(session, point_id=point.id, before_days=5, after_days=5)

    assert {row.relation_type for row in rows} == {"before_trough", "after_trough"}
