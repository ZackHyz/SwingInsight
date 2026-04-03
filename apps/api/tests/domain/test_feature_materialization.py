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
    from swinginsight.db.models.news import NewsEventResult, NewsProcessed, NewsRaw, NewsSentimentResult
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
                source_type="announcement",
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
                source_type="announcement",
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
                source_type="announcement",
                sentiment="neutral",
                data_source="tushare",
            ),
            NewsRaw(
                news_uid="n4",
                stock_code="000001",
                title="Shareholder reduction risk",
                summary="After peak capital action risk",
                publish_time=datetime(2024, 1, 10, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 10),
                source_name="source-c",
                source_type="announcement",
                sentiment="negative",
                data_source="akshare",
            ),
        ]
    )
    session.flush()

    news_ids = {
        row.news_uid: row.id
        for row in session.scalars(select(NewsRaw).where(NewsRaw.stock_code == "000001")).all()
    }
    session.add_all(
        [
            NewsProcessed(
                news_id=news_ids["n1"],
                stock_code="000001",
                category="announcement",
                sub_category="earnings",
                sentiment="positive",
                heat_level="medium",
                is_duplicate=False,
            ),
            NewsProcessed(
                news_id=news_ids["n2"],
                stock_code="000001",
                category="announcement",
                sub_category="earnings",
                sentiment="positive",
                heat_level="medium",
                is_duplicate=True,
            ),
            NewsProcessed(
                news_id=news_ids["n3"],
                stock_code="000001",
                category="announcement",
                sub_category="governance",
                sentiment="positive",
                heat_level="low",
                is_duplicate=False,
            ),
            NewsProcessed(
                news_id=news_ids["n4"],
                stock_code="000001",
                category="announcement",
                sub_category="capital_action",
                sentiment="negative",
                heat_level="high",
                is_duplicate=False,
            ),
            NewsSentimentResult(
                news_id=news_ids["n1"],
                stock_code="000001",
                sentiment_label="positive",
                sentiment_score_base=0.6,
                sentiment_score_adjusted=0.6,
                confidence_score=0.8,
                heat_score=0.45,
                market_context_score=0.0,
                position_context_score=0.0,
                event_conflict_flag=False,
                model_version="rules:v1",
                calculated_at=datetime(2024, 1, 2, 9, 5, tzinfo=UTC).replace(tzinfo=None),
            ),
            NewsSentimentResult(
                news_id=news_ids["n2"],
                stock_code="000001",
                sentiment_label="positive",
                sentiment_score_base=0.6,
                sentiment_score_adjusted=0.6,
                confidence_score=0.8,
                heat_score=0.45,
                market_context_score=0.0,
                position_context_score=0.0,
                event_conflict_flag=False,
                model_version="rules:v1",
                calculated_at=datetime(2024, 1, 2, 10, 5, tzinfo=UTC).replace(tzinfo=None),
            ),
            NewsSentimentResult(
                news_id=news_ids["n3"],
                stock_code="000001",
                sentiment_label="positive",
                sentiment_score_base=0.3,
                sentiment_score_adjusted=0.3,
                confidence_score=0.8,
                heat_score=0.3,
                market_context_score=0.0,
                position_context_score=0.0,
                event_conflict_flag=True,
                model_version="rules:v1",
                calculated_at=datetime(2024, 1, 6, 9, 5, tzinfo=UTC).replace(tzinfo=None),
            ),
            NewsSentimentResult(
                news_id=news_ids["n4"],
                stock_code="000001",
                sentiment_label="negative",
                sentiment_score_base=-0.6,
                sentiment_score_adjusted=-0.6,
                confidence_score=0.8,
                heat_score=0.8,
                market_context_score=0.0,
                position_context_score=0.0,
                event_conflict_flag=False,
                model_version="rules:v1",
                calculated_at=datetime(2024, 1, 10, 9, 5, tzinfo=UTC).replace(tzinfo=None),
            ),
            NewsEventResult(
                news_id=news_ids["n1"],
                stock_code="000001",
                sentence_index=0,
                sentence_text="Bank support policy",
                event_type="earnings",
                event_polarity="positive",
                event_strength=4,
                entity_main="000001",
                trigger_keywords=["support"],
                model_version="rules:v1",
            ),
            NewsEventResult(
                news_id=news_ids["n3"],
                stock_code="000001",
                sentence_index=0,
                sentence_text="Quarterly preview",
                event_type="earnings",
                event_polarity="positive",
                event_strength=3,
                entity_main="000001",
                trigger_keywords=["quarterly"],
                model_version="rules:v1",
            ),
            NewsEventResult(
                news_id=news_ids["n3"],
                stock_code="000001",
                sentence_index=1,
                sentence_text="Board weighs reduction",
                event_type="capital_action",
                event_polarity="negative",
                event_strength=3,
                entity_main="000001",
                trigger_keywords=["reduction"],
                model_version="rules:v1",
            ),
            NewsEventResult(
                news_id=news_ids["n4"],
                stock_code="000001",
                sentence_index=0,
                sentence_text="Shareholder reduction risk",
                event_type="capital_action",
                event_polarity="negative",
                event_strength=4,
                entity_main="000001",
                trigger_keywords=["reduction"],
                model_version="rules:v1",
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
    assert "avg_volume_5d" in names
    assert "avg_volume_10d" in names
    assert "avg_turnover_rate_5d" in names
    assert "avg_turnover_rate_10d" in names
    assert "news_count_before_trough_5d" in names
    assert "duplicate_news_ratio" in names
    assert "avg_adjusted_sentiment_before_trough_5d" in names
    assert "avg_adjusted_sentiment_after_peak_5d" in names
    assert "conflicting_event_ratio" in names
    assert "capital_action_risk_flag" in names

    feature_values = {row.feature_name: row.feature_value_num for row in rows}
    assert feature_values["avg_adjusted_sentiment_before_trough_5d"] > 0.6
    assert feature_values["avg_adjusted_sentiment_after_peak_5d"] < -0.6
    assert feature_values["conflicting_event_ratio"] > 0.0
    assert feature_values["capital_action_risk_flag"] == 1.0

    persisted = session.scalars(select(SegmentFeature).where(SegmentFeature.segment_id == segment.id)).all()
    assert len(persisted) >= 6

    labels = session.scalars(select(SegmentLabel).where(SegmentLabel.segment_id == segment.id)).all()
    label_names = {row.label_name for row in labels}
    assert "放量突破型" in label_names
    assert "消息刺激型" in label_names
