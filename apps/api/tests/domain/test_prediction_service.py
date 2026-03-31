from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_prediction_context(session):
    from swinginsight.db.models.segment import SegmentFeature, SwingSegment

    segments = [
        SwingSegment(
            segment_uid="seg-current",
            stock_code="000001",
            start_date=date(2024, 6, 1),
            end_date=date(2024, 6, 20),
            start_point_type="trough",
            end_point_type="peak",
            start_price=10.0,
            end_price=12.0,
            pct_change=20.0,
            duration_days=19,
            max_drawdown_pct=-3.0,
            max_upside_pct=22.0,
            avg_daily_change_pct=1.05,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid="seg-h1",
            stock_code="000001",
            start_date=date(2024, 4, 1),
            end_date=date(2024, 4, 16),
            start_point_type="trough",
            end_point_type="peak",
            start_price=8.0,
            end_price=9.8,
            pct_change=22.5,
            duration_days=15,
            max_drawdown_pct=-4.0,
            max_upside_pct=25.0,
            avg_daily_change_pct=1.5,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid="seg-h2",
            stock_code="000001",
            start_date=date(2024, 2, 1),
            end_date=date(2024, 2, 12),
            start_point_type="peak",
            end_point_type="trough",
            start_price=11.0,
            end_price=9.9,
            pct_change=-10.0,
            duration_days=11,
            max_drawdown_pct=-12.0,
            max_upside_pct=1.0,
            avg_daily_change_pct=-0.9,
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
            "pct_change": 20.0,
            "duration_days": 19.0,
            "max_drawdown_pct": -3.0,
            "volume_ratio_5d": 1.4,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.75,
            "duplicate_news_ratio": 0.1,
        },
        segments[1].id: {
            "pct_change": 22.5,
            "duration_days": 15.0,
            "max_drawdown_pct": -4.0,
            "volume_ratio_5d": 1.5,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.8,
            "duplicate_news_ratio": 0.0,
        },
        segments[2].id: {
            "pct_change": -10.0,
            "duration_days": 11.0,
            "max_drawdown_pct": -12.0,
            "volume_ratio_5d": 0.8,
            "ma5_above_ma20": 0.0,
            "macd_cross_flag": 0.0,
            "positive_news_ratio": 0.2,
            "duplicate_news_ratio": 0.2,
        },
    }
    for segment_id, features in feature_rows.items():
        for name, value in features.items():
            session.add(
                SegmentFeature(
                    segment_id=segment_id,
                    stock_code="000001",
                    feature_group="technical" if name in {"pct_change", "duration_days", "max_drawdown_pct", "volume_ratio_5d", "ma5_above_ma20", "macd_cross_flag"} else "news",
                    feature_name=name,
                    feature_value_num=value,
                    version_code="feature:v1",
                )
            )
    session.commit()
    return segments


def test_prediction_service_returns_state_probabilities() -> None:
    from swinginsight.services.prediction_service import PredictionService

    session = build_session()
    seed_prediction_context(session)

    result = PredictionService(session).predict("000001", date(2024, 6, 28))

    assert result.current_state in {"底部构建中", "启动前夕", "主升初期", "高位震荡", "疑似见顶"}
    assert round(result.up_prob_10d + result.flat_prob_10d + result.down_prob_10d, 4) == 1.0
    assert len(result.similar_cases) >= 1


def test_similarity_search_returns_ranked_segments() -> None:
    from swinginsight.services.prediction_service import SimilarityStore

    session = build_session()
    segments = seed_prediction_context(session)
    store = SimilarityStore(session)
    current_vector = store.load_feature_vector(segments[0].id)

    matches = store.find_top_k(current_vector=current_vector, exclude_segment_id=segments[0].id, k=2)

    assert len(matches) == 2
    assert matches[0].score >= matches[-1].score
