from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session_factory():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def seed_news_api_data(session) -> None:
    from swinginsight.db.models.news import NewsProcessed, NewsRaw, PointNewsMap, SegmentNewsMap
    from swinginsight.db.models.segment import SwingSegment
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
    segment = SwingSegment(
        segment_uid="seg-news-api",
        stock_code="000001",
        start_date=date(2024, 1, 8),
        end_date=date(2024, 1, 12),
        start_point_type="trough",
        end_point_type="peak",
        start_price=8.8,
        end_price=10.2,
        pct_change=15.0,
        duration_days=4,
        trend_direction="up",
        segment_type="up_swing",
        source_version="manual:latest",
        is_final=True,
    )
    session.add_all([point, segment])
    session.flush()

    news = NewsRaw(
        stock_code="000001",
        title="2025年业绩预告同比扭亏",
        summary="processed summary",
        publish_time=datetime(2024, 1, 7, 9, 0, tzinfo=UTC).replace(tzinfo=None),
        news_date=date(2024, 1, 7),
        source_name="cninfo",
        source_type="announcement",
        fetch_time=datetime(2024, 1, 7, 9, 5, tzinfo=UTC).replace(tzinfo=None),
        is_parsed=True,
        parse_status="processed",
        data_source="fake",
        sentiment="positive",
    )
    session.add(news)
    session.flush()

    session.add(
        NewsProcessed(
            news_id=news.id,
            stock_code="000001",
            clean_title="2025年业绩预告同比扭亏",
            clean_summary="processed summary",
            category="announcement",
            sub_category="earnings",
            sentiment="positive",
            heat_level="high",
            keyword_list=["业绩预告", "扭亏"],
            tag_list=["official", "first_release"],
            is_duplicate=False,
            processed_at=datetime(2024, 1, 7, 9, 6, tzinfo=UTC).replace(tzinfo=None),
        )
    )
    session.add(
        PointNewsMap(
            point_id=point.id,
            news_id=news.id,
            stock_code="000001",
            point_type="trough",
            relation_type="before_trough",
            anchor_date=point.point_date,
            distance_days=-1,
            weight_score=1.0,
        )
    )
    session.add(
        SegmentNewsMap(
            segment_id=segment.id,
            news_id=news.id,
            stock_code="000001",
            relation_type="before_trough",
            window_type="point_window",
            anchor_date=point.point_date,
            distance_days=-1,
            weight_score=1.0,
        )
    )
    session.commit()


def test_get_turning_point_news_returns_processed_fields() -> None:
    from swinginsight.api.main import create_app

    session_factory = build_session_factory()
    with session_factory() as session:
        seed_news_api_data(session)

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/turning-points/1/news")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["category"] == "announcement"
    assert payload[0]["sub_category"] == "earnings"
    assert payload[0]["heat_level"] == "high"
    assert payload[0]["keyword_list"] == ["业绩预告", "扭亏"]


def test_get_segment_news_returns_processed_fields() -> None:
    from swinginsight.api.main import create_app

    session_factory = build_session_factory()
    with session_factory() as session:
        seed_news_api_data(session)

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/segments/1/news")

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["category"] == "announcement"
    assert payload[0]["relation_type"] == "before_trough"
