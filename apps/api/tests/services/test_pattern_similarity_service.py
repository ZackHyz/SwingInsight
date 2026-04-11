from __future__ import annotations

from datetime import date, timedelta
import importlib.util
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

HELPER_PATH = Path(__file__).resolve().parents[1] / "domain" / "test_prediction_service.py"
HELPER_SPEC = importlib.util.spec_from_file_location("prediction_seed_helpers", HELPER_PATH)
assert HELPER_SPEC and HELPER_SPEC.loader
HELPER_MODULE = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPER_MODULE)
build_session = HELPER_MODULE.build_session
seed_prediction_context = HELPER_MODULE.seed_prediction_context


def test_pattern_similarity_service_returns_window_level_matches() -> None:
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    segments = seed_prediction_context(session)

    for stock_code in {"000001", "600157"}:
        PatternWindowService(session).build_windows(stock_code=stock_code)
        PatternFeatureService(session).materialize(stock_code=stock_code)
        PatternWindowService(session).materialize_future_stats(stock_code=stock_code)

    result = PatternSimilarityService(session).find_similar_windows(current_segment=segments[0], top_k=5)

    assert result.similar_cases
    assert result.group_stat["sample_count"] >= 1
    assert result.similar_cases[0].window_id is not None
    assert result.similar_cases[0].window_start_date is not None
    assert result.similar_cases[0].window_end_date is not None
    assert result.similar_cases[0].candle_score is not None
    assert result.similar_cases[0].trend_score is not None
    assert result.similar_cases[0].vola_score is not None


def test_pattern_similarity_service_excludes_future_windows_from_candidates() -> None:
    from sqlalchemy import func, select

    from swinginsight.db.models.pattern import PatternFeature, PatternWindow
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    segments = seed_prediction_context(session)

    for stock_code in {"000001", "600157"}:
        PatternWindowService(session).build_windows(stock_code=stock_code)
        PatternFeatureService(session).materialize(stock_code=stock_code)
        PatternWindowService(session).materialize_future_stats(stock_code=stock_code)

    current_segment = segments[0]
    total_window_count = session.scalar(select(func.count(PatternWindow.id))) or 0
    result = PatternSimilarityService(session).find_similar_windows(
        current_segment=current_segment,
        top_n=total_window_count,
        top_k=total_window_count,
    )

    assert result.query_window is not None
    query_start = result.query_window["start_date"]
    eligible_window_ids = set(
        session.scalars(
            select(PatternWindow.id)
            .join(PatternFeature, PatternFeature.window_id == PatternWindow.id)
            .where(
                PatternWindow.id != result.query_window["window_id"],
                PatternWindow.segment_id.is_not(None),
                PatternWindow.segment_id != current_segment.id,
                PatternWindow.end_date < query_start,
            )
        ).all()
    )
    returned_window_ids = {case.window_id for case in result.similar_cases}
    assert returned_window_ids
    assert returned_window_ids.issubset(eligible_window_ids)
    assert all(case.window_end_date < query_start for case in result.similar_cases if case.window_end_date is not None)


def test_pattern_similarity_service_skips_current_segment_and_non_segment_windows() -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternFutureStat, PatternWindow
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    segments = seed_prediction_context(session)

    for stock_code in {"000001", "600157"}:
        PatternWindowService(session).build_windows(stock_code=stock_code)
        PatternFeatureService(session).materialize(stock_code=stock_code)
        PatternWindowService(session).materialize_future_stats(stock_code=stock_code)

    current_segment = segments[0]

    template_window = session.query(PatternWindow).filter(PatternWindow.segment_id == current_segment.id).first()
    assert template_window is not None
    template_feature = session.query(PatternFeature).filter(PatternFeature.window_id == template_window.id).first()
    assert template_feature is not None
    template_future = session.query(PatternFutureStat).filter(PatternFutureStat.window_id == template_window.id).first()
    assert template_future is not None

    invalid_window = PatternWindow(
        window_uid="invalid:window:no-segment",
        stock_code=current_segment.stock_code,
        segment_id=None,
        start_date=template_window.start_date,
        end_date=template_window.end_date,
        window_size=template_window.window_size,
        start_close=template_window.start_close,
        end_close=template_window.end_close,
        period_pct_change=template_window.period_pct_change,
        highest_day_pos=template_window.highest_day_pos,
        lowest_day_pos=template_window.lowest_day_pos,
        trend_label=template_window.trend_label,
        feature_version=template_window.feature_version,
    )
    session.add(invalid_window)
    session.flush()
    session.add(
        PatternFeature(
            window_id=invalid_window.id,
            price_seq_json=template_feature.price_seq_json,
            return_seq_json=template_feature.return_seq_json,
            candle_feat_json=template_feature.candle_feat_json,
            volume_seq_json=template_feature.volume_seq_json,
            turnover_seq_json=template_feature.turnover_seq_json,
            trend_context_json=template_feature.trend_context_json,
            vola_context_json=template_feature.vola_context_json,
            coarse_vector_json=template_feature.coarse_vector_json,
            feature_version=template_feature.feature_version,
        )
    )
    session.add(
        PatternFutureStat(
            window_id=invalid_window.id,
            ret_1d=template_future.ret_1d,
            ret_3d=template_future.ret_3d,
            ret_5d=template_future.ret_5d,
            ret_10d=template_future.ret_10d,
            max_up_3d=template_future.max_up_3d,
            max_dd_3d=template_future.max_dd_3d,
            max_up_5d=template_future.max_up_5d,
            max_dd_5d=template_future.max_dd_5d,
            max_up_10d=template_future.max_up_10d,
            max_dd_10d=template_future.max_dd_10d,
        )
    )
    session.commit()

    result = PatternSimilarityService(session).find_similar_windows(current_segment=current_segment, top_k=5)

    assert result.similar_cases
    assert all(case.segment_id > 0 for case in result.similar_cases)
    assert all(case.segment_id != current_segment.id for case in result.similar_cases)
    assert len({case.segment_id for case in result.similar_cases}) == len(result.similar_cases)


def test_select_representative_window_prefers_segment_core_pattern_over_midpoint() -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.pattern import PatternFeature, PatternWindow
    from swinginsight.db.models.segment import SwingSegment
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService

    session = build_session()
    segment = SwingSegment(
        segment_uid="seg-core-pattern",
        stock_code="300001",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 12),
        start_point_type="trough",
        end_point_type="peak",
        start_price=10.0,
        end_price=16.5,
        pct_change=20.0,
        duration_days=10,
        max_drawdown_pct=-2.0,
        max_upside_pct=22.0,
        avg_daily_change_pct=1.8,
        segment_type="up_swing",
        trend_direction="up",
        source_version="manual:latest",
        is_final=True,
    )
    session.add(segment)
    session.flush()

    closes = [10.0, 10.4, 11.1, 11.8, 12.7, 13.6, 14.4, 15.2, 16.0, 16.2, 16.5]
    for offset, close_price in enumerate(closes):
        trade_date = segment.start_date + timedelta(days=offset)
        session.add(
            DailyPrice(
                stock_code=segment.stock_code,
                trade_date=trade_date,
                open_price=close_price - 0.2,
                high_price=close_price + 0.3,
                low_price=close_price - 0.4,
                close_price=close_price,
                volume=1_000_000 + offset * 10_000,
                turnover_rate=2.0 + offset * 0.1,
                adj_type="qfq",
                data_source="test",
            )
        )

    windows = [
        PatternWindow(
            window_uid="seg-core-pattern:w1",
            stock_code=segment.stock_code,
            segment_id=segment.id,
            start_date=date(2024, 1, 2),
            end_date=date(2024, 1, 8),
            window_size=7,
            start_close=10.0,
            end_close=14.4,
            period_pct_change=18.0,
            highest_day_pos=6,
            lowest_day_pos=0,
            trend_label="up",
            feature_version="pattern:v1",
        ),
        PatternWindow(
            window_uid="seg-core-pattern:w2",
            stock_code=segment.stock_code,
            segment_id=segment.id,
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 10),
            window_size=7,
            start_close=11.1,
            end_close=16.0,
            period_pct_change=20.0,
            highest_day_pos=5,
            lowest_day_pos=2,
            trend_label="up",
            feature_version="pattern:v1",
        ),
        PatternWindow(
            window_uid="seg-core-pattern:w3",
            stock_code=segment.stock_code,
            segment_id=segment.id,
            start_date=date(2024, 1, 6),
            end_date=date(2024, 1, 12),
            window_size=7,
            start_close=12.7,
            end_close=16.5,
            period_pct_change=12.0,
            highest_day_pos=6,
            lowest_day_pos=0,
            trend_label="up",
            feature_version="pattern:v1",
        ),
    ]
    session.add_all(windows)
    session.flush()

    feature_rows = [
        PatternFeature(
            window_id=windows[0].id,
            price_seq_json=[10.0, 10.4, 11.1, 11.8, 12.7, 13.6, 14.4],
            candle_feat_json=[0.7, 0.2, 0.1, 0.0, 1.0] * 7,
            volume_seq_json=[1.0] * 7,
            turnover_seq_json=[1.0] * 7,
            trend_context_json=[1.0, 0.9, 0.8],
            vola_context_json=[0.2, 0.2, 0.2],
            coarse_vector_json=[0.9, 0.8, 0.7],
            feature_version="pattern:v1",
        ),
        PatternFeature(
            window_id=windows[1].id,
            price_seq_json=[11.1, 10.8, 11.5, 10.6, 11.0, 10.4, 10.9],
            candle_feat_json=[0.0, 0.9, 0.8, 0.7, 0.0] * 7,
            volume_seq_json=[1.0] * 7,
            turnover_seq_json=[1.0] * 7,
            trend_context_json=[0.2, 0.9, 0.1],
            vola_context_json=[0.7, 0.8, 0.7],
            coarse_vector_json=[0.4, 0.4, 0.4],
            feature_version="pattern:v1",
        ),
        PatternFeature(
            window_id=windows[2].id,
            price_seq_json=[12.7, 13.3, 13.9, 14.6, 15.3, 16.0, 16.5],
            candle_feat_json=[0.6, 0.2, 0.1, 0.0, 1.0] * 7,
            volume_seq_json=[1.0] * 7,
            turnover_seq_json=[1.0] * 7,
            trend_context_json=[0.9, 0.8, 0.7],
            vola_context_json=[0.3, 0.3, 0.3],
            coarse_vector_json=[0.8, 0.7, 0.6],
            feature_version="pattern:v1",
        ),
    ]
    session.add_all(feature_rows)
    session.commit()

    representative = PatternSimilarityService(session).select_representative_window(segment)

    assert representative is not None
    assert representative.id == windows[0].id


def test_pattern_similarity_service_deduplicates_results_by_segment_and_stock() -> None:
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session = build_session()
    segments = seed_prediction_context(session)

    for stock_code in {"000001", "600157"}:
        PatternWindowService(session).build_windows(stock_code=stock_code)
        PatternFeatureService(session).materialize(stock_code=stock_code)
        PatternWindowService(session).materialize_future_stats(stock_code=stock_code)

    result = PatternSimilarityService(session).find_similar_windows(current_segment=segments[0], top_k=20)

    positive_segment_ids = [case.segment_id for case in result.similar_cases if case.segment_id > 0]
    assert len(positive_segment_ids) == len(set(positive_segment_ids))

    stock_counts: dict[str, int] = {}
    for case in result.similar_cases:
        stock_counts[case.stock_code] = stock_counts.get(case.stock_code, 0) + 1
    assert all(count <= 2 for count in stock_counts.values())


def test_feature_payload_uses_window_turning_points_instead_of_price_extrema() -> None:
    from swinginsight.db.models.pattern import PatternFeature, PatternWindow
    from swinginsight.services.pattern_similarity_service import PatternSimilarityService

    session = build_session()
    window = PatternWindow(
        window_uid="pw-turning-points",
        stock_code="000001",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 9),
        window_size=7,
        start_close=10.0,
        end_close=10.4,
        period_pct_change=4.0,
        highest_day_pos=1,
        lowest_day_pos=5,
        trend_label="sideways",
        feature_version="pattern:v1",
    )
    session.add(window)
    session.flush()

    feature = PatternFeature(
        window_id=window.id,
        price_seq_json=[1.0, 0.99, 1.02, 1.03, 1.01, 1.00, 1.04],
        candle_feat_json=[0.1] * 35,
        volume_seq_json=[1.0] * 7,
        turnover_seq_json=[1.0] * 7,
        trend_context_json=[1.0] * 10,
        vola_context_json=[0.1] * 5,
        coarse_vector_json=[0.0] * 21,
        feature_version="pattern:v1",
    )

    payload = PatternSimilarityService(session)._feature_payload(window, feature)

    assert payload["highest_day_pos"] == 1
    assert payload["lowest_day_pos"] == 5
