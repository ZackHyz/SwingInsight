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


def seed_segment_context(session):
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.news import NewsRaw
    from swinginsight.db.models.segment import SwingSegment

    session.add_all(
        [
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 2),
                open_price=10.0,
                high_price=10.3,
                low_price=9.9,
                close_price=10.0,
                volume=100,
                adj_type="qfq",
                data_source="demo",
            ),
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 3),
                open_price=9.8,
                high_price=9.9,
                low_price=9.2,
                close_price=9.4,
                volume=120,
                adj_type="qfq",
                data_source="demo",
            ),
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 4),
                open_price=9.2,
                high_price=9.3,
                low_price=8.7,
                close_price=8.8,
                volume=80,
                adj_type="qfq",
                data_source="demo",
            ),
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 5),
                open_price=8.9,
                high_price=9.9,
                low_price=8.9,
                close_price=9.7,
                volume=160,
                adj_type="qfq",
                data_source="demo",
            ),
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 8),
                open_price=9.8,
                high_price=10.7,
                low_price=9.7,
                close_price=10.6,
                volume=220,
                adj_type="qfq",
                data_source="demo",
            ),
        ]
    )

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
        max_drawdown_pct=-2.2727,
        max_rebound_pct=0.9434,
        max_upside_pct=21.5909,
        avg_daily_change_pct=6.8182,
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
                summary="Positive signal",
                publish_time=datetime(2024, 1, 2, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 2),
                source_name="source-a",
                sentiment="positive",
                data_source="akshare",
                duplicate_group_id="dup-1",
            ),
            NewsRaw(
                news_uid="n2",
                stock_code="000001",
                title="Bank support policy",
                summary="Duplicate signal",
                publish_time=datetime(2024, 1, 2, 10, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 2),
                source_name="source-a",
                sentiment="positive",
                data_source="akshare",
                duplicate_group_id="dup-1",
                is_duplicate=True,
            ),
            NewsRaw(
                news_uid="n3",
                stock_code="000001",
                title="Quarterly preview",
                summary="Inside segment",
                publish_time=datetime(2024, 1, 6, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 6),
                source_name="source-b",
                sentiment="neutral",
                data_source="tushare",
            ),
            NewsRaw(
                news_uid="n4",
                stock_code="000001",
                title="Earnings optimism",
                summary="Breakout catalyst",
                publish_time=datetime(2024, 1, 10, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 10),
                source_name="source-c",
                sentiment="positive",
                data_source="akshare",
            ),
        ]
    )
    session.commit()
    return segment


def test_materializer_persists_technical_and_news_features() -> None:
    from swinginsight.db.models.segment import SegmentFeature, SegmentLabel
    from swinginsight.services.feature_materialization_service import materialize_segment_features

    session = build_session()
    segment = seed_segment_context(session)

    rows = materialize_segment_features(session, segment_id=segment.id)

    names = {row.feature_name for row in rows}
    assert "pct_change" in names
    assert "news_count_before_trough_5d" in names
    assert "duplicate_news_ratio" in names

    persisted = session.scalars(select(SegmentFeature).where(SegmentFeature.segment_id == segment.id)).all()
    assert len(persisted) >= 6

    labels = session.scalars(select(SegmentLabel).where(SegmentLabel.segment_id == segment.id)).all()
    label_names = {row.label_name for row in labels}
    assert "放量突破型" in label_names
    assert "消息刺激型" in label_names
