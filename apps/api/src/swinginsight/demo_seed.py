from __future__ import annotations

from datetime import date, datetime, timedelta
import math

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice, TradeRecord
from swinginsight.db.models.news import NewsRaw, SegmentNewsMap
from swinginsight.db.models.pattern import PatternFeature, PatternFutureStat, PatternMatchResult, PatternWindow
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SegmentFeature, SegmentLabel, SwingSegment
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import PointRevisionLog, TurningPoint


DEMO_STOCK_CODE = "600157"
DEMO_STOCK_NAME = "Demo 600157"
DEMO_PREDICT_DATE = date(2026, 3, 31)
DEMO_START_DATE = date(2025, 4, 1)
DEFAULT_DEMO_DATABASE_URL = "sqlite+pysqlite:////tmp/swinginsight-demo.db"
LEGACY_DEMO_STOCK_CODES = ("000001", DEMO_STOCK_CODE)


def seed_demo_research_data(session: Session) -> dict[str, int]:
    _clear_existing_demo_rows(session)

    session.add(
        StockBasic(
            stock_code=DEMO_STOCK_CODE,
            stock_name=DEMO_STOCK_NAME,
            market="A",
            industry="Energy",
            concept_tags=["coal", "power", "demo"],
        )
    )

    prices = _build_demo_prices()
    for row in prices:
        session.add(
            DailyPrice(
                stock_code=DEMO_STOCK_CODE,
                trade_date=row["trade_date"],
                open_price=row["open_price"],
                high_price=row["high_price"],
                low_price=row["low_price"],
                close_price=row["close_price"],
                adj_type="qfq",
                data_source="demo",
            )
        )

    point_indexes = {
        "hist_trough": 34,
        "hist_peak": 86,
        "current_trough": 184,
        "current_peak": len(prices) - 9,
    }
    point_rows = {name: prices[index] for name, index in point_indexes.items()}

    session.add_all(
        [
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=point_rows["current_trough"]["trade_date"],
                point_type="trough",
                point_price=point_rows["current_trough"]["low_price"],
                source_type="system",
                version_code="zigzag:demo",
                is_final=False,
            ),
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=point_rows["current_peak"]["trade_date"],
                point_type="peak",
                point_price=point_rows["current_peak"]["high_price"],
                source_type="system",
                version_code="zigzag:demo",
                is_final=False,
            ),
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=point_rows["current_trough"]["trade_date"],
                point_type="trough",
                point_price=point_rows["current_trough"]["low_price"],
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
                created_by="demo-seed",
            ),
            TurningPoint(
                stock_code=DEMO_STOCK_CODE,
                point_date=point_rows["current_peak"]["trade_date"],
                point_type="peak",
                point_price=point_rows["current_peak"]["high_price"],
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
            segment_uid=f"{DEMO_STOCK_CODE}:{point_rows['current_trough']['trade_date']:%Y-%m-%d}:{point_rows['current_peak']['trade_date']:%Y-%m-%d}:manual:latest",
            stock_code=DEMO_STOCK_CODE,
            start_date=point_rows["current_trough"]["trade_date"],
            end_date=point_rows["current_peak"]["trade_date"],
            start_point_type="trough",
            end_point_type="peak",
            start_price=point_rows["current_trough"]["low_price"],
            end_price=point_rows["current_peak"]["high_price"],
            pct_change=21.8421,
            duration_days=(point_rows["current_peak"]["trade_date"] - point_rows["current_trough"]["trade_date"]).days,
            max_drawdown_pct=-4.1,
            max_upside_pct=24.3,
            avg_daily_change_pct=1.18,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid=f"{DEMO_STOCK_CODE}:{point_rows['hist_trough']['trade_date']:%Y-%m-%d}:{point_rows['hist_peak']['trade_date']:%Y-%m-%d}:manual:latest",
            stock_code=DEMO_STOCK_CODE,
            start_date=point_rows["hist_trough"]["trade_date"],
            end_date=point_rows["hist_peak"]["trade_date"],
            start_point_type="trough",
            end_point_type="peak",
            start_price=point_rows["hist_trough"]["low_price"],
            end_price=point_rows["hist_peak"]["high_price"],
            pct_change=18.425,
            duration_days=(point_rows["hist_peak"]["trade_date"] - point_rows["hist_trough"]["trade_date"]).days,
            max_drawdown_pct=-5.3,
            max_upside_pct=20.7,
            avg_daily_change_pct=0.74,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid=f"{DEMO_STOCK_CODE}:2025-11-03:2025-12-08:manual:latest",
            stock_code=DEMO_STOCK_CODE,
            start_date=date(2025, 11, 3),
            end_date=date(2025, 12, 8),
            start_point_type="peak",
            end_point_type="trough",
            start_price=6.12,
            end_price=5.11,
            pct_change=-16.5033,
            duration_days=35,
            max_drawdown_pct=-18.8,
            max_upside_pct=1.5,
            avg_daily_change_pct=-0.47,
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
            "pct_change": 21.8421,
            "duration_days": float(segments[0].duration_days),
            "max_drawdown_pct": -4.1,
            "volume_ratio_5d": 1.52,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.7,
            "duplicate_news_ratio": 0.0,
        },
        segments[1].id: {
            "pct_change": 18.425,
            "duration_days": float(segments[1].duration_days),
            "max_drawdown_pct": -5.3,
            "volume_ratio_5d": 1.34,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.65,
            "duplicate_news_ratio": 0.1,
        },
        segments[2].id: {
            "pct_change": -16.5033,
            "duration_days": float(segments[2].duration_days),
            "max_drawdown_pct": -18.8,
            "volume_ratio_5d": 0.78,
            "ma5_above_ma20": 0.0,
            "macd_cross_flag": 0.0,
            "positive_news_ratio": 0.3,
            "duplicate_news_ratio": 0.2,
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
        (segments[1].id, "放量突破型", 0.85),
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

    news_dates = [
        point_rows["current_trough"]["trade_date"] - timedelta(days=2),
        point_rows["current_peak"]["trade_date"] - timedelta(days=1),
    ]
    session.add_all(
        [
            NewsRaw(
                stock_code=DEMO_STOCK_CODE,
                title="Thermal coal benchmark stabilises into spring demand",
                summary="Sector sentiment improves ahead of the rebound leg.",
                content="Demo news item",
                publish_time=datetime.combine(news_dates[0], datetime.min.time()).replace(hour=9, minute=30),
                news_date=news_dates[0],
                source_name="demo-wire",
                source_type="demo",
                sentiment="positive",
                news_type="macro",
                is_duplicate=False,
                data_source="demo",
            ),
            NewsRaw(
                stock_code=DEMO_STOCK_CODE,
                title="Power dispatch update supports utility-linked names",
                summary="Follow-through catalyst during the latest advance.",
                content="Demo news item",
                publish_time=datetime.combine(news_dates[1], datetime.min.time()).replace(hour=10, minute=0),
                news_date=news_dates[1],
                source_name="demo-wire",
                source_type="demo",
                sentiment="positive",
                news_type="sector",
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
                anchor_date=point_rows["current_trough"]["trade_date"],
                distance_days=(news_rows[0].news_date - point_rows["current_trough"]["trade_date"]).days,
                weight_score=1.0,
            ),
            SegmentNewsMap(
                segment_id=segments[0].id,
                news_id=news_rows[1].id,
                stock_code=DEMO_STOCK_CODE,
                relation_type="inside_segment",
                window_type="segment_body",
                anchor_date=point_rows["current_trough"]["trade_date"],
                distance_days=(news_rows[1].news_date - point_rows["current_trough"]["trade_date"]).days,
                weight_score=1.0,
            ),
        ]
    )

    session.add_all(
        [
            TradeRecord(
                stock_code=DEMO_STOCK_CODE,
                trade_date=point_rows["current_trough"]["trade_date"] + timedelta(days=5),
                trade_type="buy",
                price=round(point_rows["current_trough"]["close_price"] * 1.03, 4),
                quantity=3000,
                amount=round(point_rows["current_trough"]["close_price"] * 1.03 * 3000, 2),
                strategy_tag="demo",
                order_group_id="demo-buy-1",
                note="Seeded momentum entry",
                source="demo",
            ),
            TradeRecord(
                stock_code=DEMO_STOCK_CODE,
                trade_date=point_rows["current_peak"]["trade_date"] - timedelta(days=2),
                trade_type="sell",
                price=round(point_rows["current_peak"]["close_price"] * 0.98, 4),
                quantity=1500,
                amount=round(point_rows["current_peak"]["close_price"] * 0.98 * 1500, 2),
                strategy_tag="demo",
                order_group_id="demo-sell-1",
                note="Seeded scale-out",
                source="demo",
            ),
        ]
    )

    session.add(
        PredictionResult(
            stock_code=DEMO_STOCK_CODE,
            predict_date=DEMO_PREDICT_DATE,
            current_state="主升初期",
            up_prob_5d=0.61,
            flat_prob_5d=0.22,
            down_prob_5d=0.17,
            up_prob_10d=0.57,
            flat_prob_10d=0.23,
            down_prob_10d=0.20,
            up_prob_20d=0.48,
            flat_prob_20d=0.26,
            down_prob_20d=0.26,
            similarity_topn_json=[
                {
                    "segment_id": segments[1].id,
                    "stock_code": DEMO_STOCK_CODE,
                    "score": 0.91,
                    "pct_change": 18.425,
                },
                {
                    "segment_id": segments[2].id,
                    "stock_code": DEMO_STOCK_CODE,
                    "score": 0.24,
                    "pct_change": -16.5033,
                },
            ],
            key_features_json={
                "pct_change": 21.8421,
                "volume_ratio_5d": 1.52,
                "positive_news_ratio": 0.7,
                "max_drawdown_pct": -4.1,
            },
            risk_flags_json={"pullback_risk": "low", "news_support": "strong"},
            model_version="prediction:v1",
            summary="主升初期，10日上行概率 0.57",
        )
    )

    session.flush()
    return {
        "stock_code": DEMO_STOCK_CODE,
        "segment_id": segments[0].id,
        "prediction_date": DEMO_PREDICT_DATE.toordinal(),
    }


def _build_demo_prices() -> list[dict[str, float | date]]:
    rows: list[dict[str, float | date]] = []
    current_date = DEMO_START_DATE
    index = 0
    previous_close = 4.82

    while current_date <= DEMO_PREDICT_DATE:
        if current_date.weekday() >= 5:
            current_date += timedelta(days=1)
            continue

        seasonal = math.sin(index / 10) * 0.48
        drift = index * 0.0045
        correction = -0.35 if 120 <= index <= 145 else 0
        close_price = round(max(3.85, 4.65 + seasonal + drift + correction), 4)
        open_price = round(close_price + math.sin(index / 3) * 0.08, 4)
        high_price = round(max(open_price, close_price) + 0.12 + (index % 5) * 0.015, 4)
        low_price = round(min(open_price, close_price) - 0.11 - (index % 4) * 0.012, 4)
        rows.append(
            {
                "trade_date": current_date,
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "close_price": close_price,
                "pre_close_price": previous_close,
            }
        )
        previous_close = close_price
        current_date += timedelta(days=1)
        index += 1

    return rows


def _clear_existing_demo_rows(session: Session) -> None:
    demo_window_ids = select(PatternWindow.id).where(PatternWindow.stock_code.in_(LEGACY_DEMO_STOCK_CODES))
    session.execute(
        delete(PatternMatchResult).where(
            PatternMatchResult.target_window_id.in_(demo_window_ids) | PatternMatchResult.query_window_id.in_(demo_window_ids)
        )
    )
    session.execute(delete(PatternFutureStat).where(PatternFutureStat.window_id.in_(demo_window_ids)))
    session.execute(delete(PatternFeature).where(PatternFeature.window_id.in_(demo_window_ids)))
    session.execute(delete(PatternWindow).where(PatternWindow.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(PointRevisionLog).where(PointRevisionLog.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(SegmentNewsMap).where(SegmentNewsMap.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(SegmentLabel).where(SegmentLabel.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(SegmentFeature).where(SegmentFeature.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(PredictionResult).where(PredictionResult.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(TradeRecord).where(TradeRecord.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(NewsRaw).where(NewsRaw.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(SwingSegment).where(SwingSegment.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(TurningPoint).where(TurningPoint.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(DailyPrice).where(DailyPrice.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
    session.execute(delete(StockBasic).where(StockBasic.stock_code.in_(LEGACY_DEMO_STOCK_CODES)))
