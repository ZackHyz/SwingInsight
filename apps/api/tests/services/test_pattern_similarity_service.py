from __future__ import annotations

from datetime import date
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

    # Add a high-similarity rolling window without a segment mapping. It should never leak into the UI payload.
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
