from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


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


def test_pattern_insight_endpoints_return_expected_payloads(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.api.routes import stocks as stocks_route

    def fake_summary(*_args, **_kwargs):
        return {
            "similar_cases": [
                {
                    "segment_id": 11,
                    "stock_code": "600157",
                    "score": 0.9,
                    "window_id": 101,
                    "window_start_date": "2025-01-03",
                    "window_end_date": "2025-01-13",
                    "segment_start_date": "2024-12-30",
                    "segment_end_date": "2025-01-20",
                    "return_5d": 0.04,
                    "return_10d": 0.08,
                    "return_20d": 0.11,
                },
                {
                    "segment_id": 12,
                    "stock_code": "600157",
                    "score": 0.7,
                    "window_id": 102,
                    "window_start_date": "2024-11-03",
                    "window_end_date": "2024-11-13",
                    "segment_start_date": "2024-11-01",
                    "segment_end_date": "2024-11-20",
                    "return_5d": -0.03,
                    "return_10d": -0.01,
                    "return_20d": 0.02,
                },
            ]
        }

    monkeypatch.setattr(stocks_route, "load_latest_prediction_summary", fake_summary)
    monkeypatch.setattr(
        stocks_route.PatternScoreCalibrationService,
        "predict_with_meta",
        lambda self, **kwargs: (
            0.5934 if int(kwargs.get("horizon_days") or 10) == 5 else 0.5712,
            True,
        ),
    )

    app = create_app(session_factory=build_session_factory())
    client = TestClient(app)

    score_response = client.get("/stocks/600157/pattern-score")
    assert score_response.status_code == 200
    score_payload = score_response.json()
    assert score_payload["horizon_days"] == 10
    assert score_payload["sample_count"] == 2
    assert score_payload["confidence"] == "low"
    assert score_payload["raw_win_rate"] == 0.5
    assert score_payload["win_rate_5d"] == 0.5934
    assert score_payload["win_rate_10d"] == 0.5712
    assert score_payload["win_rate"] == 0.5712
    assert score_payload["calibrated"] is True
    assert score_payload["avg_return"] > 0

    cases_response = client.get("/stocks/600157/similar-cases")
    assert cases_response.status_code == 200
    cases_payload = cases_response.json()
    assert len(cases_payload) == 2
    assert cases_payload[0]["window_id"] == 101
    assert cases_payload[0]["similarity_score"] == 0.9
    assert cases_payload[0]["future_return_10d"] == 0.08
    assert cases_payload[0]["future_return_20d"] == 0.11

    stat_response = client.get("/stocks/600157/group-stat")
    assert stat_response.status_code == 200
    stat_payload = stat_response.json()
    assert stat_payload["horizon_days"] == [5, 10, 20]
    assert stat_payload["win_rates"] == [0.5, 0.5, 1.0]
    assert len(stat_payload["avg_returns"]) == 3
    assert stat_payload["sample_counts"] == [2, 2, 2]
    assert stat_payload["return_distribution"] == [-0.01, 0.08]
    assert stat_payload["return_distributions"] == {
        "5": [-0.03, 0.04],
        "10": [-0.01, 0.08],
        "20": [0.02, 0.11],
    }


def test_pattern_insight_endpoints_return_404_when_prediction_missing(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.api.routes import stocks as stocks_route

    monkeypatch.setattr(stocks_route, "load_latest_prediction_summary", lambda *_args, **_kwargs: None)
    app = create_app(session_factory=build_session_factory())
    client = TestClient(app)

    assert client.get("/stocks/600157/pattern-score").status_code == 404
    assert client.get("/stocks/600157/similar-cases").status_code == 404
    assert client.get("/stocks/600157/group-stat").status_code == 404
