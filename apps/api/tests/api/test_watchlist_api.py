from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sys

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session_factory():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def test_watchlist_endpoint_returns_latest_scan_rows() -> None:
    from swinginsight.api.main import create_app
    from swinginsight.services.market_watchlist_service import MarketWatchlistService

    session_factory = build_session_factory()
    session = session_factory()
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.news import NewsRaw
    from swinginsight.db.models.prediction import PredictionResult
    from swinginsight.db.models.stock import StockBasic

    session.add_all(
        [
            StockBasic(stock_code="000001", stock_name="Ping An Bank", market="A", industry="Bank", concept_tags=["finance"]),
            StockBasic(stock_code="600157", stock_name="Yongtai Energy", market="A", industry="Coal", concept_tags=["energy"]),
        ]
    )
    for stock_code in ["000001", "600157"]:
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=date(2026, 4, 16),
                open_price=10.0,
                high_price=10.3,
                low_price=9.8,
                close_price=10.1,
                adj_type="qfq",
                data_source="test",
            )
        )
    session.add_all(
        [
            PredictionResult(
                stock_code="000001",
                predict_date=date(2026, 4, 16),
                current_state="up",
                up_prob_5d=0.6,
                flat_prob_5d=0.2,
                down_prob_5d=0.2,
                up_prob_10d=0.66,
                flat_prob_10d=0.2,
                down_prob_10d=0.14,
                up_prob_20d=0.58,
                flat_prob_20d=0.22,
                down_prob_20d=0.2,
                similarity_topn_json=[{"id": 1}, {"id": 2}, {"id": 3}],
                key_features_json={},
                risk_flags_json={},
                model_version="prediction:v1",
                summary="s1",
            ),
            PredictionResult(
                stock_code="600157",
                predict_date=date(2026, 4, 16),
                current_state="flat",
                up_prob_5d=0.45,
                flat_prob_5d=0.31,
                down_prob_5d=0.24,
                up_prob_10d=0.43,
                flat_prob_10d=0.32,
                down_prob_10d=0.25,
                up_prob_20d=0.42,
                flat_prob_20d=0.33,
                down_prob_20d=0.25,
                similarity_topn_json=[{"id": 9}],
                key_features_json={},
                risk_flags_json={},
                model_version="prediction:v1",
                summary="s2",
            ),
        ]
    )
    for idx in range(2):
        session.add(
            NewsRaw(
                news_uid=f"n-{idx}",
                stock_code="000001",
                title=f"000001 news {idx}",
                summary=None,
                content=None,
                publish_time=datetime(2026, 4, 16, 9, 0),
                news_date=date(2026, 4, 16) - timedelta(days=idx),
                source_name="test",
                source_type="news",
                url=f"https://example.com/{idx}",
                data_source="test",
            )
        )
    MarketWatchlistService(session).run_scan(scan_date=date(2026, 4, 16))
    session.commit()
    session.close()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/watchlist")

    assert response.status_code == 200
    payload = response.json()
    assert payload["scan_date"] == "2026-04-16"
    assert payload["rows"]
    assert payload["rows"][0]["stock_code"] == "000001"
    assert payload["rows"][0]["rank_no"] == 1


def test_watchlist_refresh_endpoint_rebuilds_latest_rows(monkeypatch) -> None:
    from swinginsight.api.main import create_app
    from swinginsight.services.market_watchlist_service import MarketWatchlistService

    session_factory = build_session_factory()
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    def fake_refresh(self, *, limit: int = 30) -> dict[str, object]:
        return {
            "scan_date": "2026-04-17",
            "rows": [
                {
                    "stock_code": "600010",
                    "stock_name": "包钢股份",
                    "rank_no": 1,
                    "rank_score": 0.81,
                    "pattern_score": 0.79,
                    "confidence": 1.0,
                    "sample_count": 8,
                    "event_density": 0.15,
                    "latest_refresh_at": "2026-04-17T00:00:00",
                }
            ],
        }

    monkeypatch.setattr(MarketWatchlistService, "refresh_watchlist", fake_refresh)

    response = client.post("/watchlist/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"queued", "running", "success"}

    status_response = client.get("/watchlist/refresh-status")
    assert status_response.status_code == 200
    status_payload = status_response.json()
    assert status_payload["status"] == "success"
    assert status_payload["scan_date"] == "2026-04-17"
    assert status_payload["row_count"] == 1
