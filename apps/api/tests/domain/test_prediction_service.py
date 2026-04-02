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
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.segment import SegmentFeature, SwingSegment

    segments = [
        SwingSegment(
            segment_uid="seg-current",
            stock_code="000001",
            start_date=date(2024, 6, 3),
            end_date=date(2024, 6, 7),
            start_point_type="trough",
            end_point_type="peak",
            start_price=10.0,
            end_price=12.0,
            pct_change=20.0,
            duration_days=4,
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
            end_date=date(2024, 4, 5),
            start_point_type="trough",
            end_point_type="peak",
            start_price=8.0,
            end_price=9.8,
            pct_change=22.5,
            duration_days=4,
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
            end_date=date(2024, 2, 5),
            start_point_type="peak",
            end_point_type="trough",
            start_price=11.0,
            end_price=9.9,
            pct_change=-10.0,
            duration_days=4,
            max_drawdown_pct=-12.0,
            max_upside_pct=1.0,
            avg_daily_change_pct=-0.9,
            segment_type="down_swing",
            trend_direction="down",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid="seg-h3",
            stock_code="000001",
            start_date=date(2024, 5, 6),
            end_date=date(2024, 5, 10),
            start_point_type="trough",
            end_point_type="peak",
            start_price=9.2,
            end_price=11.0,
            pct_change=19.5652,
            duration_days=4,
            max_drawdown_pct=-3.5,
            max_upside_pct=21.0,
            avg_daily_change_pct=1.3,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
        SwingSegment(
            segment_uid="seg-h4-cross",
            stock_code="600157",
            start_date=date(2024, 3, 11),
            end_date=date(2024, 3, 15),
            start_point_type="trough",
            end_point_type="peak",
            start_price=10.0,
            end_price=12.0,
            pct_change=20.0,
            duration_days=4,
            max_drawdown_pct=-3.0,
            max_upside_pct=22.0,
            avg_daily_change_pct=1.05,
            segment_type="up_swing",
            trend_direction="up",
            source_version="manual:latest",
            is_final=True,
        ),
    ]
    session.add_all(segments)
    session.flush()

    price_rows = [
        ("000001", date(2024, 2, 1), 11.0, 11.1, 10.7, 10.8, 820000, 1.3),
        ("000001", date(2024, 2, 2), 10.8, 10.9, 10.2, 10.4, 860000, 1.4),
        ("000001", date(2024, 2, 5), 10.3, 10.4, 9.8, 9.9, 910000, 1.6),
        ("000001", date(2024, 2, 6), 9.9, 10.0, 9.6, 9.7, 950000, 1.7),
        ("000001", date(2024, 2, 7), 9.7, 9.8, 9.5, 9.6, 980000, 1.8),
        ("000001", date(2024, 2, 8), 9.6, 9.7, 9.4, 9.5, 990000, 1.8),
        ("000001", date(2024, 2, 9), 9.5, 9.6, 9.3, 9.4, 1010000, 1.9),
        ("000001", date(2024, 4, 1), 8.0, 8.2, 7.9, 8.1, 1500000, 2.5),
        ("000001", date(2024, 4, 2), 8.1, 8.5, 8.0, 8.4, 1550000, 2.6),
        ("000001", date(2024, 4, 3), 8.4, 8.9, 8.3, 8.8, 1620000, 2.7),
        ("000001", date(2024, 4, 4), 8.8, 9.3, 8.7, 9.1, 1700000, 2.8),
        ("000001", date(2024, 4, 5), 9.1, 9.9, 9.0, 9.8, 1780000, 2.9),
        ("000001", date(2024, 4, 8), 9.8, 10.1, 9.7, 10.0, 1760000, 2.8),
        ("000001", date(2024, 4, 9), 10.0, 10.2, 9.9, 10.1, 1720000, 2.7),
        ("000001", date(2024, 4, 10), 10.1, 10.3, 10.0, 10.2, 1680000, 2.6),
        ("000001", date(2024, 4, 11), 10.2, 10.4, 10.0, 10.1, 1640000, 2.5),
        ("000001", date(2024, 4, 12), 10.1, 10.3, 9.9, 9.9, 1600000, 2.4),
        ("000001", date(2024, 4, 15), 9.9, 10.0, 9.7, 9.8, 1580000, 2.3),
        ("000001", date(2024, 5, 6), 9.2, 9.4, 9.1, 9.3, 1450000, 2.4),
        ("000001", date(2024, 5, 7), 9.3, 9.8, 9.2, 9.7, 1500000, 2.5),
        ("000001", date(2024, 5, 8), 9.7, 10.3, 9.6, 10.1, 1560000, 2.6),
        ("000001", date(2024, 5, 9), 10.1, 10.7, 10.0, 10.5, 1610000, 2.7),
        ("000001", date(2024, 5, 10), 10.5, 11.2, 10.4, 11.0, 1680000, 2.8),
        ("000001", date(2024, 5, 13), 11.0, 11.1, 10.8, 10.9, 1620000, 2.6),
        ("000001", date(2024, 5, 14), 10.9, 11.0, 10.6, 10.7, 1580000, 2.5),
        ("000001", date(2024, 5, 15), 10.7, 10.9, 10.5, 10.6, 1540000, 2.4),
        ("000001", date(2024, 5, 16), 10.6, 10.8, 10.4, 10.5, 1500000, 2.3),
        ("000001", date(2024, 5, 17), 10.5, 10.6, 10.2, 10.3, 1460000, 2.2),
        ("000001", date(2024, 5, 20), 10.3, 10.4, 10.0, 10.1, 1420000, 2.1),
        ("000001", date(2024, 6, 3), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        ("000001", date(2024, 6, 4), 10.1, 10.5, 10.0, 10.4, 1520000, 2.7),
        ("000001", date(2024, 6, 5), 10.4, 10.9, 10.3, 10.8, 1600000, 2.8),
        ("000001", date(2024, 6, 6), 10.8, 11.2, 10.7, 11.0, 1700000, 2.9),
        ("000001", date(2024, 6, 7), 11.0, 12.2, 10.9, 12.0, 1800000, 3.0),
        ("600157", date(2024, 3, 11), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        ("600157", date(2024, 3, 12), 10.1, 10.5, 10.0, 10.4, 1520000, 2.7),
        ("600157", date(2024, 3, 13), 10.4, 10.9, 10.3, 10.8, 1600000, 2.8),
        ("600157", date(2024, 3, 14), 10.8, 11.2, 10.7, 11.0, 1700000, 2.9),
        ("600157", date(2024, 3, 15), 11.0, 12.2, 10.9, 12.0, 1800000, 3.0),
        ("600157", date(2024, 3, 18), 12.0, 12.4, 11.9, 12.3, 1760000, 2.9),
        ("600157", date(2024, 3, 19), 12.3, 12.5, 12.0, 12.1, 1720000, 2.8),
        ("600157", date(2024, 3, 20), 12.1, 12.8, 12.0, 12.6, 1690000, 2.8),
        ("600157", date(2024, 3, 21), 12.6, 13.1, 12.5, 13.0, 1650000, 2.7),
        ("600157", date(2024, 3, 22), 13.0, 13.1, 12.7, 12.8, 1610000, 2.6),
        ("600157", date(2024, 3, 25), 12.8, 13.6, 12.7, 13.4, 1580000, 2.5),
        ("600157", date(2024, 3, 26), 13.4, 13.6, 13.2, 13.5, 1540000, 2.4),
        ("600157", date(2024, 3, 27), 13.5, 13.6, 13.0, 13.2, 1510000, 2.4),
        ("600157", date(2024, 3, 28), 13.2, 13.3, 12.9, 13.1, 1480000, 2.3),
        ("600157", date(2024, 3, 29), 13.1, 13.9, 13.0, 13.8, 1450000, 2.2),
    ]
    for stock_code, trade_date, open_price, high_price, low_price, close_price, volume, turnover_rate in price_rows:
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                turnover_rate=turnover_rate,
                adj_type="qfq",
                data_source="test",
            )
        )

    feature_rows = {
        segments[0].id: {
            "pct_change": 20.0,
            "duration_days": 4.0,
            "max_drawdown_pct": -3.0,
            "volume_ratio_5d": 1.4,
            "avg_volume_5d": 1500000.0,
            "avg_volume_10d": 1420000.0,
            "avg_turnover_rate_5d": 2.8,
            "avg_turnover_rate_10d": 2.5,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.75,
            "duplicate_news_ratio": 0.1,
        },
        segments[1].id: {
            "pct_change": 22.5,
            "duration_days": 4.0,
            "max_drawdown_pct": -4.0,
            "volume_ratio_5d": 1.5,
            "avg_volume_5d": 1520000.0,
            "avg_volume_10d": 1405000.0,
            "avg_turnover_rate_5d": 2.9,
            "avg_turnover_rate_10d": 2.4,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.8,
            "duplicate_news_ratio": 0.0,
        },
        segments[2].id: {
            "pct_change": -10.0,
            "duration_days": 4.0,
            "max_drawdown_pct": -12.0,
            "volume_ratio_5d": 0.8,
            "avg_volume_5d": 600000.0,
            "avg_volume_10d": 720000.0,
            "avg_turnover_rate_5d": 1.1,
            "avg_turnover_rate_10d": 1.3,
            "ma5_above_ma20": 0.0,
            "macd_cross_flag": 0.0,
            "positive_news_ratio": 0.2,
            "duplicate_news_ratio": 0.2,
        },
        segments[3].id: {
            "pct_change": 19.5652,
            "duration_days": 4.0,
            "max_drawdown_pct": -3.5,
            "volume_ratio_5d": 1.35,
            "avg_volume_5d": 1510000.0,
            "avg_volume_10d": 1435000.0,
            "avg_turnover_rate_5d": 2.7,
            "avg_turnover_rate_10d": 2.5,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.72,
            "duplicate_news_ratio": 0.05,
        },
        segments[4].id: {
            "pct_change": 20.0,
            "duration_days": 4.0,
            "max_drawdown_pct": -3.0,
            "volume_ratio_5d": 1.4,
            "avg_volume_5d": 1500000.0,
            "avg_volume_10d": 1420000.0,
            "avg_turnover_rate_5d": 2.8,
            "avg_turnover_rate_10d": 2.5,
            "ma5_above_ma20": 1.0,
            "macd_cross_flag": 1.0,
            "positive_news_ratio": 0.75,
            "duplicate_news_ratio": 0.1,
        },
    }
    segment_lookup = {segment.id: segment for segment in segments}
    for segment_id, features in feature_rows.items():
        for name, value in features.items():
            session.add(
                SegmentFeature(
                    segment_id=segment_id,
                    stock_code=segment_lookup[segment_id].stock_code,
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
    assert round(result.up_prob_1d + result.flat_prob_1d + result.down_prob_1d, 4) == 1.0
    assert round(result.up_prob_10d + result.flat_prob_10d + result.down_prob_10d, 4) == 1.0
    assert len(result.similar_cases) >= 1


def test_similarity_search_returns_ranked_segments() -> None:
    from swinginsight.services.prediction_service import SimilarityStore

    session = build_session()
    segments = seed_prediction_context(session)
    store = SimilarityStore(session)
    current_vector = store.load_feature_vector(segments[0].id)

    matches = store.find_top_k(current_segment=segments[0], current_vector=current_vector, k=4)

    assert len(matches) == 4
    assert [match.stock_code for match in matches] == ["000001", "000001", "000001", "600157"]
    assert {match.segment_id for match in matches[:2]} == {segments[1].id, segments[3].id}
    assert matches[-1].segment_id == segments[4].id
    assert matches[-1].score > matches[0].score
    assert 0.0 <= matches[0].price_score <= 1.0
    assert 0.0 <= matches[0].volume_score <= 1.0
    assert 0.0 <= matches[0].turnover_score <= 1.0
    assert 0.0 <= matches[0].pattern_score <= 1.0
    assert matches[-1].forward_returns[1] is not None
    assert matches[-1].forward_returns[3] is not None
    assert matches[-1].forward_returns[5] is not None
    assert matches[-1].forward_returns[10] is not None


def test_similarity_search_penalizes_candidates_with_large_bar_count_gap() -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.segment import SegmentFeature, SwingSegment
    from swinginsight.services.prediction_service import SimilarityStore

    session = build_session()
    segments = seed_prediction_context(session)

    long_segment = SwingSegment(
        segment_uid="seg-h5-long",
        stock_code="000001",
        start_date=date(2024, 3, 1),
        end_date=date(2024, 3, 15),
        start_point_type="trough",
        end_point_type="peak",
        start_price=10.0,
        end_price=12.0,
        pct_change=20.0,
        duration_days=14,
        max_drawdown_pct=-3.0,
        max_upside_pct=22.0,
        avg_daily_change_pct=1.05,
        segment_type="up_swing",
        trend_direction="up",
        source_version="manual:latest",
        is_final=True,
    )
    session.add(long_segment)
    session.flush()

    padded_current_rows = [
        (date(2024, 3, 1), 9.7, 9.9, 9.6, 9.8, 1300000, 2.2),
        (date(2024, 3, 2), 9.8, 10.0, 9.7, 9.9, 1310000, 2.2),
        (date(2024, 3, 3), 9.9, 10.1, 9.8, 10.0, 1320000, 2.3),
        (date(2024, 3, 4), 10.0, 10.2, 9.9, 10.1, 1330000, 2.3),
        (date(2024, 3, 5), 10.1, 10.3, 10.0, 10.1, 1340000, 2.4),
        (date(2024, 3, 6), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        (date(2024, 3, 7), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        (date(2024, 3, 8), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        (date(2024, 3, 9), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        (date(2024, 3, 10), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        (date(2024, 3, 11), 10.0, 10.2, 9.9, 10.1, 1480000, 2.6),
        (date(2024, 3, 12), 10.1, 10.5, 10.0, 10.4, 1520000, 2.7),
        (date(2024, 3, 13), 10.4, 10.9, 10.3, 10.8, 1600000, 2.8),
        (date(2024, 3, 14), 10.8, 11.2, 10.7, 11.0, 1700000, 2.9),
        (date(2024, 3, 15), 11.0, 12.2, 10.9, 12.0, 1800000, 3.0),
    ]
    for trade_date, open_price, high_price, low_price, close_price, volume, turnover_rate in padded_current_rows:
        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                volume=volume,
                turnover_rate=turnover_rate,
                adj_type="qfq",
                data_source="test",
            )
        )

    for name, value in {
        "pct_change": 20.0,
        "duration_days": 14.0,
        "max_drawdown_pct": -3.0,
        "volume_ratio_5d": 1.4,
        "avg_volume_5d": 1500000.0,
        "avg_volume_10d": 1420000.0,
        "avg_turnover_rate_5d": 2.8,
        "avg_turnover_rate_10d": 2.5,
        "ma5_above_ma20": 1.0,
        "macd_cross_flag": 1.0,
        "positive_news_ratio": 0.75,
        "duplicate_news_ratio": 0.1,
    }.items():
        session.add(
            SegmentFeature(
                segment_id=long_segment.id,
                stock_code="000001",
                feature_group="technical" if name in {"pct_change", "duration_days", "max_drawdown_pct", "volume_ratio_5d", "ma5_above_ma20", "macd_cross_flag"} else "news",
                feature_name=name,
                feature_value_num=value,
                version_code="feature:v1",
            )
        )
    session.commit()

    store = SimilarityStore(session)
    current_vector = store.load_feature_vector(segments[0].id)

    matches = store.find_top_k(current_segment=segments[0], current_vector=current_vector, k=4)

    assert matches[0].segment_id != long_segment.id
    assert matches.index(next(match for match in matches if match.segment_id == long_segment.id)) > matches.index(
        next(match for match in matches if match.segment_id == segments[1].id)
    )


def test_prediction_service_estimates_each_horizon_independently() -> None:
    from swinginsight.services.prediction_service import SimilarCase, PredictionService

    session = build_session()
    service = PredictionService(session)

    probabilities = service._estimate_probabilities(
        [
            SimilarCase(
                segment_id=1,
                stock_code="000001",
                score=0.92,
                price_score=0.78,
                volume_score=0.7,
                turnover_score=0.74,
                pattern_score=0.8,
                pct_change=6.0,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                forward_returns={1: 0.025, 5: -0.04, 10: 0.01, 20: 0.08},
            ),
            SimilarCase(
                segment_id=2,
                stock_code="000001",
                score=0.85,
                price_score=0.72,
                volume_score=0.66,
                turnover_score=0.7,
                pattern_score=0.75,
                pct_change=4.0,
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 10),
                forward_returns={1: 0.018, 5: -0.03, 10: -0.02, 20: 0.06},
            ),
            SimilarCase(
                segment_id=3,
                stock_code="000001",
                score=0.8,
                price_score=0.68,
                volume_score=0.61,
                turnover_score=0.64,
                pattern_score=0.7,
                pct_change=-3.0,
                start_date=date(2024, 3, 1),
                end_date=date(2024, 3, 10),
                forward_returns={1: -0.015, 5: -0.05, 10: -0.06, 20: -0.09},
            ),
        ]
    )

    assert probabilities["up_1d"] > probabilities["down_1d"]
    assert probabilities["down_5d"] > probabilities["up_5d"]
    assert probabilities["up_1d"] != probabilities["up_5d"]
    assert probabilities["up_10d"] != probabilities["up_20d"]


def test_prediction_service_applies_smoothing_when_similar_cases_are_one_sided() -> None:
    from swinginsight.services.prediction_service import SimilarCase, PredictionService

    session = build_session()
    service = PredictionService(session)

    probabilities = service._estimate_probabilities(
        [
            SimilarCase(
                segment_id=1,
                stock_code="000001",
                score=0.98,
                price_score=0.72,
                volume_score=0.65,
                turnover_score=0.61,
                pattern_score=0.7,
                pct_change=-12.0,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 10),
                forward_returns={1: -0.02, 5: -0.08, 10: -0.12, 20: -0.16},
            ),
            SimilarCase(
                segment_id=2,
                stock_code="000001",
                score=0.94,
                price_score=0.68,
                volume_score=0.62,
                turnover_score=0.6,
                pattern_score=0.66,
                pct_change=-8.0,
                start_date=date(2024, 2, 1),
                end_date=date(2024, 2, 10),
                forward_returns={1: -0.015, 5: -0.07, 10: -0.09, 20: -0.12},
            ),
            SimilarCase(
                segment_id=3,
                stock_code="000001",
                score=0.91,
                price_score=0.64,
                volume_score=0.59,
                turnover_score=0.57,
                pattern_score=0.63,
                pct_change=-6.5,
                start_date=date(2024, 3, 1),
                end_date=date(2024, 3, 10),
                forward_returns={1: -0.01, 5: -0.05, 10: -0.08, 20: -0.11},
            ),
        ]
    )

    assert 0 < probabilities["up_1d"] < 0.25
    assert 0 < probabilities["flat_1d"] < 0.25
    assert 0.5 < probabilities["down_1d"] < 1.0
    assert 0 < probabilities["up_10d"] < 0.2
    assert 0 < probabilities["flat_10d"] < 0.2
    assert 0.6 < probabilities["down_10d"] < 1.0


def test_prediction_payload_includes_sample_forward_return_fields() -> None:
    from swinginsight.api.routes.predictions import get_prediction_payload

    session = build_session()
    seed_prediction_context(session)

    payload = get_prediction_payload(session, "000001", date(2024, 6, 28))

    assert payload["similar_cases"]
    sample = next(item for item in payload["similar_cases"] if item["stock_code"] == "600157")
    assert sample["stock_code"] == "600157"
    assert sample["return_1d"] is not None
    assert sample["return_3d"] is not None
    assert sample["return_5d"] is not None
    assert sample["return_10d"] is not None
