from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session_factory():
    from swinginsight.db.base import Base
    from swinginsight.db import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def test_score_validation_api_returns_report(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.api import main as main_module

    class StubValidationService:
        def __init__(self, _session):
            pass

        def build_validation_report(self, *, stock_code: str):
            assert stock_code == "600157"
            return {"evaluated_samples_10d": 20, "brier_score_10d": 0.19, "pass_gate": True}

    monkeypatch.setattr(main_module, "ScoreValidationService", StubValidationService)

    app = create_app(session_factory=build_session_factory())
    client = TestClient(app)

    response = client.get("/stocks/600157/score-validation")
    assert response.status_code == 200
    payload = response.json()
    assert payload["evaluated_samples_10d"] == 20
    assert payload["pass_gate"] is True
