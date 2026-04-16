from __future__ import annotations

from datetime import datetime
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


def test_post_refresh_enqueues_task_and_returns_status() -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app

    app = create_app(session_factory=build_session_factory())
    client = TestClient(app)

    response = client.post("/stocks/600010/refresh")

    assert response.status_code == 200
    payload = response.json()
    assert isinstance(payload["task_id"], int)
    assert payload["stock_code"] == "600010"
    assert payload["status"] == "queued"
    assert payload["created_at"]
    assert payload["reused"] is False


def test_get_refresh_status_returns_latest_task_payload() -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.db.models.refresh import StockRefreshStageLog, StockRefreshTask

    session_factory = build_session_factory()
    session = session_factory()
    task = StockRefreshTask(
        stock_code="600010",
        status="success",
        start_time=datetime(2026, 4, 16, 9, 0, 0),
        end_time=datetime(2026, 4, 16, 9, 5, 0),
    )
    session.add(task)
    session.commit()
    session.refresh(task)
    session.add(
        StockRefreshStageLog(
            task_id=task.id,
            stage_name="price_import",
            status="success",
            source="akshare",
            rows_changed=3,
            start_time=datetime(2026, 4, 16, 9, 0, 0),
            end_time=datetime(2026, 4, 16, 9, 1, 0),
            duration_ms=60000,
        )
    )
    session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/stocks/600010/refresh-status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["task_id"] == task.id
    assert payload["stock_code"] == "600010"
    assert payload["status"] == "success"
    assert payload["created_at"]
    assert payload["start_time"] == "2026-04-16T09:00:00"
    assert payload["end_time"] == "2026-04-16T09:05:00"
    assert payload["error_message"] is None
    assert payload["stages"] == [
        {
            "stage_name": "price_import",
            "status": "success",
            "source": "akshare",
            "rows_changed": 3,
            "start_time": "2026-04-16T09:00:00",
            "end_time": "2026-04-16T09:01:00",
            "duration_ms": 60000,
            "error_message": None,
        }
    ]


def test_get_refresh_status_returns_404_when_missing() -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app

    app = create_app(session_factory=build_session_factory())
    client = TestClient(app)

    response = client.get("/stocks/600010/refresh-status")

    assert response.status_code == 404
    assert response.json() == {"detail": "refresh task not found"}
