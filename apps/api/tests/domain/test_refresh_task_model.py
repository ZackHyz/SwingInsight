from __future__ import annotations

from datetime import UTC, datetime
import importlib.util
from pathlib import Path
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.sqlite import dialect as sqlite_dialect
import pytest


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


def test_refresh_task_rejects_second_inflight_task_for_same_stock() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.refresh import StockRefreshTask

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    Session = sessionmaker(bind=engine, future=True, expire_on_commit=False)
    with Session() as session:
        session.add(
            StockRefreshTask(
                stock_code="600010",
                status="queued",
            )
        )
        session.commit()

        session.add(
            StockRefreshTask(
                stock_code="600010",
                status="running",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_refresh_task_migration_uses_sqlite_safe_pk_and_fk_types(monkeypatch) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "alembic" / "versions" / "0008_refresh_task.py"
    spec = importlib.util.spec_from_file_location("refresh_task_migration", migration_path)
    assert spec and spec.loader
    migration_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration_module)

    tables: dict[str, dict[str, object]] = {}

    def fake_create_table(name: str, *columns, **_kwargs) -> None:
        tables[name] = {column.name: column for column in columns}

    monkeypatch.setattr(migration_module.op, "create_table", fake_create_table)
    monkeypatch.setattr(migration_module.op, "create_index", lambda *args, **kwargs: None)

    migration_module.upgrade()

    sqlite_impl = sqlite_dialect()
    task_columns = tables["stock_refresh_task"]
    stage_columns = tables["stock_refresh_stage_log"]

    assert task_columns["id"].type.compile(dialect=sqlite_impl) == "INTEGER"
    assert stage_columns["id"].type.compile(dialect=sqlite_impl) == "INTEGER"
    assert stage_columns["task_id"].type.compile(dialect=sqlite_impl) == "INTEGER"
