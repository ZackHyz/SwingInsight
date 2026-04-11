from __future__ import annotations

from datetime import date
import importlib.util
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


HELPER_PATH = Path(__file__).resolve().parents[1] / "domain" / "test_prediction_service.py"
HELPER_SPEC = importlib.util.spec_from_file_location("prediction_seed_helpers", HELPER_PATH)
assert HELPER_SPEC and HELPER_SPEC.loader
HELPER_MODULE = importlib.util.module_from_spec(HELPER_SPEC)
HELPER_SPEC.loader.exec_module(HELPER_MODULE)
seed_prediction_context = HELPER_MODULE.seed_prediction_context


def build_session_factory():
    from swinginsight.db.base import Base

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def test_pattern_similarity_flow_runs_end_to_end() -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.services.pattern_feature_service import PatternFeatureService
    from swinginsight.services.pattern_window_service import PatternWindowService

    session_factory = build_session_factory()
    with session_factory() as session:
      seed_prediction_context(session)
      for stock_code in {"000001", "600157"}:
          PatternWindowService(session).build_windows(stock_code=stock_code)
          PatternFeatureService(session).materialize(stock_code=stock_code)
          PatternWindowService(session).materialize_future_stats(stock_code=stock_code)
      session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/predictions/000001", params={"predict_date": date(2024, 6, 28).isoformat()})

    assert response.status_code == 200
    payload = response.json()
    assert payload["similar_cases"]
    assert payload["group_stat"]["sample_count"] >= 1
    assert payload["query_window"]["window_size"] == 7
    assert payload["query_window"]["start_date"] is not None
    assert payload["query_window"]["end_date"] is not None
    assert payload["similar_cases"][0]["window_start_date"] is not None
    assert payload["similar_cases"][0]["window_end_date"] is not None
    assert payload["similar_cases"][0]["segment_start_date"] is not None
    assert payload["similar_cases"][0]["segment_end_date"] is not None
    query_start = payload["query_window"]["start_date"]
    assert all(
        item["window_end_date"] < query_start
        for item in payload["similar_cases"]
        if item["window_end_date"] is not None
    )
    positive_segment_ids = [item["segment_id"] for item in payload["similar_cases"] if item["segment_id"] is not None and item["segment_id"] > 0]
    assert len(positive_segment_ids) == len(set(positive_segment_ids))
