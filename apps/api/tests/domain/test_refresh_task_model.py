from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_refresh_task_tables_exist_and_insert_work() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.refresh import StockRefreshStageLog, StockRefreshTask

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    inspector = inspect(engine)
    assert "stock_refresh_task" in inspector.get_table_names()
    assert "stock_refresh_stage_log" in inspector.get_table_names()

    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with Session() as session:
        task = StockRefreshTask(
            stock_code="600010",
            status="running",
            start_time=datetime(2026, 4, 16, 10, 0, tzinfo=UTC).replace(tzinfo=None),
        )
        session.add(task)
        session.flush()

        stage_log = StockRefreshStageLog(
            task_id=task.id,
            stage_name="price_import",
            status="success",
            source="akshare",
            rows_changed=12,
            start_time=datetime(2026, 4, 16, 10, 1, tzinfo=UTC).replace(tzinfo=None),
            end_time=datetime(2026, 4, 16, 10, 2, tzinfo=UTC).replace(tzinfo=None),
            duration_ms=60000,
        )
        session.add(stage_log)
        session.commit()

        assert task.id is not None
        assert stage_log.id is not None
