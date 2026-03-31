from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice, TradeRecord
from swinginsight.db.models.news import NewsRaw, SegmentNewsMap
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SegmentFeature, SegmentLabel, SwingSegment
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import PointRevisionLog, TurningPoint


DEMO_STOCK_CODE = "000001"
DEMO_PREDICT_DATE = date(2024, 6, 28)
DEFAULT_DEMO_DATABASE_URL = "sqlite+pysqlite:////tmp/swinginsight-demo.db"


def seed_demo_research_data(session: Session) -> dict[str, int]:
    _clear_existing_demo_rows(session)

    session.add(
        StockBasic(
            stock_code=DEMO_STOCK_CODE,
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=["finance", "bluechip"],
        )
    )

    prices = [
        (date(2024, 6, 17), 10.1, 10.3, 9.9, 10.0),
        (date(2024, 6, 18), 9.9, 10.0, 9.4, 9.6),
        (date(2024, 6, 19), 9.6, 10.2, 9.5, 10.1),
        (date(2024, 6, 20), 10.2, 10.9, 10.1, 10.8),
        (date(2024, 6, 21), 10.8, 11.4, 10.7, 11.3),
        (date(2024, 6, 24), 11.2, 12.2, 11.1, 12.0),
        (date(2024, 6, 25), 12.0, 12.1, 11.5, 11.7),
        (date(2024, 6, 26), 11.7, 11.8, 11.2, 11.4),
        (date(2024, 6, 27), 11.4, 11.9, 11.3, 11.8),
        (date(2024, 6, 28), 11.8, 12.3, 11.7, 12.1),
    ]
    for trade_date, open_price, high_price, low_price, close_price in prices:
        session.add(
            DailyPrice(
                stock_code=DEMO_STOCK_CODE,
                trade_date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                adj_type="qfq",
                data_source="demo",
            )
        )

    session.add_all(
        [
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=date(2024, 6, 18),
                point_type="trough",
                point_price=9.6,
                source_type="system",
                version_code="zigzag:demo",
                is_final=False,
            ),
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=date(2024, 6, 24),
                point_type="peak",
                point_price=12.0,
                source_type="system",
                version_code="zigzag:demo",
                is_final=False,
            ),
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=date(2024, 6, 18),
                point_type="trough",
                point_price=9.6,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
                created_by="demo-seed",
            ),
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=date(2024, 6, 24),
                point_type="peak",
                point_price=12.0,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
                created_by="demo-seed",
            ),
        ]
    )
    session.add(
        PointRevisionLog(
            stock_code=DEMO_STOCK_CODE,
            operation_type="seed",
            old_value_json=None,
            new_value_json={"version_code": "manual:latest"},
            operator="demo-seed",
            remark="Initial seeded manual turning points",
        )
    )

    segments = [
        SwingSegment(
            segment_uid="000001:2024-06-18:2024-06-24:manual:latest",
            stock_code=DEMO_STOCK_CODE,
            start_date=date(2024, 6, 18),
            end_date=date(2024, 6, 24),
            start_point_type="trough",
            end_point_type="peak",
            start_price=9.6,
            end_price=12.0,
            pct_change=25.0,
            duration_days=6,
            max_drawdown_pct=-2.1,
            max_upside_pct=26.2,
            avg_daily_change_pct=3.6,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid="000001:2024-04-02:2024-04-18:manual:latest",
            stock_code=DEMO_STOCK_CODE,
            start_date=date(2024, 4, 2),
            end_date=date(2024, 4, 18),
            start_point_type="trough",
            end_point_type="peak",
            start_price=8.1,
            end_price=10.0,
            pct_change=23.4568,
            duration_days=16,
            max_drawdown_pct=-4.2,
            max_upside_pct=24.0,
            avg_daily_change_pct=1.46,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid="000001:2024-02-06:2024-02-19:manual:latest",
            stock_code=DEMO_STOCK_CODE,
            start_date=date(2024, 2, 6),
            end_date=date(2024, 2, 19),
            start_point_type="peak",
            end_point_type="trough",
            start_price=11.2,
            end_price=10.0,
            pct_change=-10.7143,
            duration_days=13,
            max_drawdown_pct=-12.4,
            max_upside_pct=1.3,
            avg_daily_change_pct=-0.82,
            segment_type="down_swing",
            trend_direction="down",
            source_version="manual:latest",
            is_final=True,
        ),
    ]
    session.add_all(segments)
    session.flush()

    feature_rows = {
        segments[0].id: {
            "pct_change": 25.0,
            "duration_days": 6.0,
            "max_drawdown_pct": -2.1,
            "volume_ratio_5d": 1.6,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.75,
            "duplicate_news_ratio": 0.0,
        },
        segments[1].id: {
            "pct_change": 23.4568,
            "duration_days": 16.0,
            "max_drawdown_pct": -4.2,
            "volume_ratio_5d": 1.45,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.8,
            "duplicate_news_ratio": 0.1,
        },
        segments[2].id: {
            "pct_change": -10.7143,
            "duration_days": 13.0,
            "max_drawdown_pct": -12.4,
            "volume_ratio_5d": 0.82,
            "ma5_above_ma20": 0.0,
            "macd_cross_flag": 0.0,
            "positive_news_ratio": 0.25,
            "duplicate_news_ratio": 0.25,
        },
    }
    for segment_id, features in feature_rows.items():
        for name, value in features.items():
            session.add(
                SegmentFeature(
                    segment_id=segment_id,
                    stock_code=DEMO_STOCK_CODE,
                    feature_group="technical"
                    if name in {"pct_change", "duration_days", "max_drawdown_pct", "volume_ratio_5d", "ma5_above_ma20", "macd_cross_flag"}
                    else "news",
                    feature_name=name,
                    feature_value_num=value,
                    version_code="feature:v1",
                )
            )

    for segment_id, label_name, score in (
        (segments[0].id, "放量突破型", 0.9),
        (segments[0].id, "消息刺激型", 0.8),
        (segments[1].id, "放量突破型", 0.9),
        (segments[2].id, "高位见顶型", 0.8),
    ):
        session.add(
            SegmentLabel(
                segment_id=segment_id,
                stock_code=DEMO_STOCK_CODE,
                label_type="pattern",
                label_name=label_name,
                label_value="matched",
                score=score,
                source_type="system",
                version_code="feature:v1",
            )
        )

    session.add_all(
        [
            NewsRaw(
                stock_code=DEMO_STOCK_CODE,
                title="Credit growth supports banking names",
                summary="Macro data improves into the trough.",
                content="Demo news item",
                publish_time=datetime(2024, 6, 17, 9, 30),
                news_date=date(2024, 6, 17),
                source_name="demo-wire",
                source_type="demo",
                sentiment="positive",
                news_type="macro",
                is_duplicate=False,
                data_source="demo",
            ),
            NewsRaw(
                stock_code=DEMO_STOCK_CODE,
                title="Broker notes highlight margin recovery",
                summary="Analysts call out improving trading activity.",
                content="Demo news item",
                publish_time=datetime(2024, 6, 21, 10, 0),
                news_date=date(2024, 6, 21),
                source_name="demo-wire",
                source_type="demo",
                sentiment="positive",
                news_type="broker",
                is_duplicate=False,
                data_source="demo",
            ),
        ]
    )
    session.flush()

    news_rows = session.scalars(
        select(NewsRaw).where(NewsRaw.stock_code == DEMO_STOCK_CODE).order_by(NewsRaw.news_date.asc(), NewsRaw.id.asc())
    ).all()
    session.add_all(
        [
            SegmentNewsMap(
                segment_id=segments[0].id,
                news_id=news_rows[0].id,
                stock_code=DEMO_STOCK_CODE,
                relation_type="before_trough",
                window_type="point_window",
                anchor_date=date(2024, 6, 18),
                distance_days=-1,
                weight_score=1.0,
            ),
            SegmentNewsMap(
                segment_id=segments[0].id,
                news_id=news_rows[1].id,
                stock_code=DEMO_STOCK_CODE,
                relation_type="inside_segment",
                window_type="segment_body",
                anchor_date=date(2024, 6, 18),
                distance_days=3,
                weight_score=1.0,
            ),
        ]
    )

    session.add(
        TradeRecord(
            stock_code=DEMO_STOCK_CODE,
            trade_date=date(2024, 6, 20),
            trade_type="buy",
            price=10.8,
            quantity=1000,
            amount=10800,
            strategy_tag="demo",
            order_group_id="demo-buy-1",
            note="Seeded demo buy marker",
            source="demo",
        )
    )

    session.add(
        PredictionResult(
            stock_code=DEMO_STOCK_CODE,
            predict_date=DEMO_PREDICT_DATE,
            current_state="主升初期",
            up_prob_5d=0.62,
            flat_prob_5d=0.21,
            down_prob_5d=0.17,
            up_prob_10d=0.58,
            flat_prob_10d=0.22,
            down_prob_10d=0.20,
            up_prob_20d=0.49,
            flat_prob_20d=0.25,
            down_prob_20d=0.26,
            similarity_topn_json=[
                {
                    "segment_id": segments[1].id,
                    "stock_code": DEMO_STOCK_CODE,
                    "score": 0.93,
                    "pct_change": 23.4568,
                },
                {
                    "segment_id": segments[2].id,
                    "stock_code": DEMO_STOCK_CODE,
                    "score": 0.21,
                    "pct_change": -10.7143,
                },
            ],
            key_features_json={
                "pct_change": 25.0,
                "volume_ratio_5d": 1.6,
                "positive_news_ratio": 0.75,
                "max_drawdown_pct": -2.1,
            },
            risk_flags_json={"pullback_risk": "low", "news_support": "strong"},
            model_version="prediction:v1",
            summary="主升初期，10日上行概率 0.58",
        )
    )

    session.flush()
    return {
        "stock_code": DEMO_STOCK_CODE,
        "segment_id": segments[0].id,
        "prediction_date": DEMO_PREDICT_DATE.toordinal(),
    }


def _clear_existing_demo_rows(session: Session) -> None:
    session.execute(delete(PointRevisionLog).where(PointRevisionLog.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(SegmentNewsMap).where(SegmentNewsMap.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(SegmentLabel).where(SegmentLabel.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(SegmentFeature).where(SegmentFeature.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(PredictionResult).where(PredictionResult.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(TradeRecord).where(TradeRecord.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(NewsRaw).where(NewsRaw.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(SwingSegment).where(SwingSegment.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(TurningPoint).where(TurningPoint.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(DailyPrice).where(DailyPrice.stock_code == DEMO_STOCK_CODE))
    session.execute(delete(StockBasic).where(StockBasic.stock_code == DEMO_STOCK_CODE))
