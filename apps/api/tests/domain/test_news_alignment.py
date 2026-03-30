from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_segment_and_news(session):
    from swinginsight.db.models.news import NewsRaw
    from swinginsight.db.models.segment import SwingSegment

    segment = SwingSegment(
        segment_uid="seg-1",
        stock_code="000001",
        start_date=date(2024, 1, 4),
        end_date=date(2024, 1, 8),
        start_point_type="trough",
        end_point_type="peak",
        start_price=8.8,
        end_price=10.6,
        pct_change=20.4545,
        duration_days=4,
        trend_direction="up",
        segment_type="up_swing",
        source_version="manual:latest",
        is_final=True,
    )
    session.add(segment)
    session.flush()

    session.add_all(
        [
            NewsRaw(
                news_uid="n1",
                stock_code="000001",
                title="Bank support policy",
                summary="Support before trough",
                publish_time=datetime(2024, 1, 2, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 2),
                source_name="source-a",
                source_type="news",
                data_source="akshare",
            ),
            NewsRaw(
                news_uid="n2",
                stock_code="000001",
                title="Bank support policy",
                summary="Duplicate title same source",
                publish_time=datetime(2024, 1, 2, 10, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 2),
                source_name="source-a",
                source_type="news",
                data_source="akshare",
            ),
            NewsRaw(
                news_uid="n3",
                stock_code="000001",
                title="Quarterly preview",
                summary="Inside segment",
                publish_time=datetime(2024, 1, 6, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 6),
                source_name="source-b",
                source_type="news",
                data_source="tushare",
            ),
            NewsRaw(
                news_uid="n4",
                stock_code="000001",
                title="Earnings optimism",
                summary="After peak",
                publish_time=datetime(2024, 1, 10, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 10),
                source_name="source-c",
                source_type="news",
                data_source="akshare",
            ),
        ]
    )
    session.commit()
    return segment


def test_alignment_maps_news_within_point_window() -> None:
    from swinginsight.db.models.news import SegmentNewsMap
    from swinginsight.services.segment_news_alignment_service import align_segment_news

    session = build_session()
    segment = seed_segment_and_news(session)

    rows = align_segment_news(session, segment_id=segment.id, before_days=5, after_days=5)

    assert len(rows) == 3
    assert any(row.relation_type == "before_trough" for row in rows)
    assert any(row.relation_type == "inside_segment" for row in rows)
    assert any(row.relation_type == "after_peak" for row in rows)

    persisted = session.scalars(select(SegmentNewsMap).where(SegmentNewsMap.segment_id == segment.id)).all()
    assert len(persisted) == 3
    before_row = next(row for row in persisted if row.relation_type == "before_trough")
    assert before_row.distance_days == -2


def test_dedupe_groups_same_title_and_source() -> None:
    from swinginsight.domain.news.dedupe import dedupe_news_items

    grouped = dedupe_news_items(
        [
            {"id": 1, "title": "Bank support policy", "source_name": "source-a", "news_date": date(2024, 1, 2)},
            {"id": 2, "title": "Bank support policy", "source_name": "source-a", "news_date": date(2024, 1, 2)},
            {"id": 3, "title": "Bank support policy", "source_name": "source-b", "news_date": date(2024, 1, 2)},
        ]
    )

    assert len(grouped) == 2
