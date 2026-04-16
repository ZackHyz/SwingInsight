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


def seed_materialized_stock(session) -> None:
    from swinginsight.db.models.stock import StockBasic

    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=["finance"],
        )
    )
    session.commit()


def test_get_stock_reads_materialized_payload_without_refresh(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.services.stock_research_service import StockResearchService

    session_factory = build_session_factory()
    seed_materialized_stock(session_factory())

    monkeypatch.setattr(
        StockResearchService,
        "ensure_stock_ready",
        lambda self, stock_code: (_ for _ in ()).throw(AssertionError("ensure_stock_ready should not be called")),
    )

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/stocks/000001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stock"]["stock_code"] == "000001"
    assert payload["prices"] == []
    assert payload["auto_turning_points"] == []
    assert payload["final_turning_points"] == []


def test_get_stock_returns_404_when_materialized_payload_missing_without_refresh(monkeypatch) -> None:
    from fastapi.testclient import TestClient

    from swinginsight.api.main import create_app
    from swinginsight.services.stock_research_service import StockResearchService

    monkeypatch.setattr(
        StockResearchService,
        "ensure_stock_ready",
        lambda self, stock_code: (_ for _ in ()).throw(AssertionError("ensure_stock_ready should not be called")),
    )

    app = create_app(session_factory=build_session_factory())
    client = TestClient(app)

    response = client.get("/stocks/000001")

    assert response.status_code == 404
    assert response.json() == {"detail": "stock not found"}
