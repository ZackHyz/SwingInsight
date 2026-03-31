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


def test_end_to_end_research_flow() -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.demo_seed import DEMO_PREDICT_DATE, DEMO_STOCK_CODE, seed_demo_research_data

    session_factory = build_session_factory()
    with session_factory() as session:
        seed_demo_research_data(session)
        session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    prediction_response = client.get(
        f"/predictions/{DEMO_STOCK_CODE}",
        params={"predict_date": DEMO_PREDICT_DATE.isoformat()},
    )

    assert prediction_response.status_code == 200
    prediction_payload = prediction_response.json()
    assert prediction_payload["stock_code"] == DEMO_STOCK_CODE
    assert "current_state" in prediction_payload
    assert prediction_payload["similar_cases"]

    research_response = client.get(f"/stocks/{DEMO_STOCK_CODE}")

    assert research_response.status_code == 200
    research_payload = research_response.json()
    assert research_payload["stock"]["stock_code"] == DEMO_STOCK_CODE
    assert research_payload["prices"]
    assert research_payload["final_turning_points"]
    assert research_payload["current_state"]["label"] != "placeholder"
