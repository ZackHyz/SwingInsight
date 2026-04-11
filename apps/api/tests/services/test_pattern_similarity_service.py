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
                PatternWindow.end_date < query_start,
            )
        ).all()
    )
    assert {case.window_id for case in result.similar_cases} == eligible_window_ids
    assert all(case.window_end_date < query_start for case in result.similar_cases if case.window_end_date is not None)
