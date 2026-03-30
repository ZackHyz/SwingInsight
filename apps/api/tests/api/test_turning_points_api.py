from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
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


def seed_research_data(session: Session) -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.segment import SwingSegment
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.db.models.turning_point import TurningPoint

    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=["finance", "bluechip"],
        )
    )
    prices = [
        (date(2024, 1, 2), 10.0, 10.2, 9.8, 10.0),
        (date(2024, 1, 3), 9.8, 9.9, 9.2, 9.4),
        (date(2024, 1, 4), 9.2, 9.3, 8.7, 8.8),
        (date(2024, 1, 5), 8.9, 9.9, 8.9, 9.7),
        (date(2024, 1, 8), 9.8, 10.7, 9.7, 10.6),
        (date(2024, 1, 9), 10.4, 10.5, 9.6, 9.8),
        (date(2024, 1, 10), 9.4, 9.5, 8.8, 8.9),
        (date(2024, 1, 11), 9.1, 10.0, 9.0, 9.9),
        (date(2024, 1, 12), 10.2, 11.0, 10.1, 10.9),
    ]
    for trade_date, open_price, high_price, low_price, close_price in prices:
        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                adj_type="qfq",
                data_source="test",
            )
        )

    session.add_all(
        [
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 4),
                point_type="trough",
                point_price=8.8,
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 8),
                point_type="peak",
                point_price=10.6,
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 4),
                point_type="trough",
                point_price=8.8,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 8),
                point_type="peak",
                point_price=10.6,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
        ]
    )
    session.add(
        SwingSegment(
            segment_uid="000001:2024-01-04:2024-01-08:manual:latest",
            stock_code="000001",
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 8),
            start_point_type="trough",
            end_point_type="peak",
            start_price=8.8,
            end_price=10.6,
            pct_change=20.4545,
            duration_days=4,
            trend_direction="up",
            segment_type="up_swing",
            source_version="manual:latest",
            is_final=True,
        )
    )
    session.commit()


def test_get_stock_research_payload_contains_expected_sections() -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app

    session_factory = build_session_factory()
    session = session_factory()
    seed_research_data(session)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/stocks/000001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stock"]["stock_code"] == "000001"
    assert len(payload["prices"]) == 9
    assert len(payload["auto_turning_points"]) == 2
    assert len(payload["final_turning_points"]) == 2
    assert payload["current_state"]["label"] == "placeholder"


def test_commit_turning_points_persists_logs_and_rebuilds_segments() -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.segment import SwingSegment
    from swinginsight.db.models.turning_point import PointRevisionLog, TurningPoint

    session_factory = build_session_factory()
    session = session_factory()
    seed_research_data(session)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.post(
        "/stocks/000001/turning-points/commit",
        json={
            "operator": "tester",
            "operations": [
                {
                    "operation_type": "move",
                    "old_value": {"point_date": "2024-01-04", "point_type": "trough", "point_price": 8.8},
                    "new_value": {"point_date": "2024-01-03", "point_type": "trough", "point_price": 9.4},
                },
                {
                    "operation_type": "add",
                    "old_value": None,
                    "new_value": {"point_date": "2024-01-10", "point_type": "trough", "point_price": 8.9},
                },
            ],
            "final_points": [
                {"point_date": "2024-01-03", "point_type": "trough", "point_price": 9.4},
                {"point_date": "2024-01-08", "point_type": "peak", "point_price": 10.6},
                {"point_date": "2024-01-10", "point_type": "trough", "point_price": 8.9},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rebuild_summary"]["segments"] == 2
    assert len(payload["final_turning_points"]) == 3

    final_points = session.scalars(
        select(TurningPoint).where(TurningPoint.stock_code == "000001", TurningPoint.is_final.is_(True))
    ).all()
    assert len(final_points) == 3
    assert {point.source_type for point in final_points} == {"manual"}

    revision_logs = session.scalars(select(PointRevisionLog)).all()
    assert len(revision_logs) == 2
    assert revision_logs[0].operator == "tester"

    segments = session.scalars(select(SwingSegment).where(SwingSegment.stock_code == "000001")).all()
    assert len(segments) == 2
