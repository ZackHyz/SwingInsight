from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def test_enqueue_refresh_reuses_running_task() -> None:
    from swinginsight.db.models.refresh import StockRefreshTask
    from swinginsight.services.stock_refresh_service import StockRefreshService

    session = build_session()
    service = StockRefreshService(session)

    first = service.enqueue("600010")
    first.status = "running"
    session.flush()

    second = service.enqueue("600010")

    tasks = session.scalars(select(StockRefreshTask).where(StockRefreshTask.stock_code == "600010")).all()
    assert first.id == second.id
    assert len(tasks) == 1


def test_run_records_stage_transitions_for_success_path(monkeypatch) -> None:
    from swinginsight.db.models.refresh import StockRefreshStageLog
    from swinginsight.jobs.align_news import AlignNewsResult
    from swinginsight.jobs.process_news import ProcessNewsResult
    from swinginsight.services import stock_research_service as stock_research_module
    from swinginsight.services.stock_refresh_service import StockRefreshService

    session = build_session()
    service = StockRefreshService(session)
    task = service.enqueue("600010")

    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "prepare_refresh",
        lambda self, stock_code: stock_research_module.RefreshPreparation(
            latest_trade_date_before_refresh=date(2026, 4, 15),
            should_refresh_remote=True,
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "refresh_live_prices",
        lambda self, stock_code, latest_trade_date: stock_research_module.PriceRefreshResult(
            source="akshare",
            inserted=3,
            updated=2,
            skipped=0,
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "load_latest_trade_date",
        lambda self, stock_code: date(2026, 4, 16),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "needs_rebuild",
        lambda self, *, stock_code, latest_trade_date: True,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "resolve_news_window",
        lambda self, *, anchor_date: (date(2026, 4, 2), date(2026, 4, 16)),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "import_news_window",
        lambda self, stock_code, *, start_date, end_date: 5,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "process_news_window",
        lambda self, stock_code, *, start_date, end_date: ProcessNewsResult(processed_count=4, duplicates=1),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "align_news_window",
        lambda self, stock_code, *, start_date, end_date: AlignNewsResult(point_mappings=2, segment_mappings=3),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "materialize_refresh_artifacts",
        lambda self, *, stock_code, latest_trade_date, needs_rebuild, has_live_price_updates, news_refresh: 7,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "predict_for_refresh",
        lambda self, *, stock_code, latest_trade_date: object(),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "stock_exists",
        lambda self, stock_code: True,
    )

    updated_task = service.run(task.id)
    stage_logs = session.scalars(
        select(StockRefreshStageLog)
        .where(StockRefreshStageLog.task_id == task.id)
        .order_by(StockRefreshStageLog.id.asc())
    ).all()

    assert updated_task.status == "success"
    assert [log.stage_name for log in stage_logs] == [
        "price_import",
        "news_import",
        "news_process",
        "news_align",
        "pattern_materialize",
        "prediction",
    ]
    assert [log.status for log in stage_logs] == ["success"] * 6
    assert [log.rows_changed for log in stage_logs] == [5, 5, 4, 5, 7, 1]
    assert stage_logs[0].source == "akshare"
    assert stage_logs[-1].source == "prediction_service"
    assert all(log.duration_ms is not None for log in stage_logs)
    assert updated_task.start_time is not None
    assert updated_task.end_time is not None

    latest_status = service.latest_status("600010")

    assert latest_status is not None
    assert latest_status["task_id"] == task.id
    assert latest_status["status"] == "success"
    assert [stage["stage_name"] for stage in latest_status["stages"]] == [
        "price_import",
        "news_import",
        "news_process",
        "news_align",
        "pattern_materialize",
        "prediction",
    ]


def test_run_marks_partial_when_late_stage_fails(monkeypatch) -> None:
    from swinginsight.db.models.refresh import StockRefreshStageLog
    from swinginsight.jobs.align_news import AlignNewsResult
    from swinginsight.jobs.process_news import ProcessNewsResult
    from swinginsight.services import stock_research_service as stock_research_module
    from swinginsight.services.stock_refresh_service import StockRefreshService

    session = build_session()
    service = StockRefreshService(session)
    task = service.enqueue("600010")

    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "prepare_refresh",
        lambda self, stock_code: stock_research_module.RefreshPreparation(
            latest_trade_date_before_refresh=date(2026, 4, 15),
            should_refresh_remote=True,
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "refresh_live_prices",
        lambda self, stock_code, latest_trade_date: stock_research_module.PriceRefreshResult(
            source="akshare",
            inserted=1,
            updated=0,
            skipped=0,
        ),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "load_latest_trade_date",
        lambda self, stock_code: date(2026, 4, 16),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "needs_rebuild",
        lambda self, *, stock_code, latest_trade_date: False,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "resolve_news_window",
        lambda self, *, anchor_date: (date(2026, 4, 2), date(2026, 4, 16)),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "import_news_window",
        lambda self, stock_code, *, start_date, end_date: 1,
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "process_news_window",
        lambda self, stock_code, *, start_date, end_date: ProcessNewsResult(processed_count=1, duplicates=0),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "align_news_window",
        lambda self, stock_code, *, start_date, end_date: AlignNewsResult(point_mappings=1, segment_mappings=0),
    )
    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "materialize_refresh_artifacts",
        lambda self, *, stock_code, latest_trade_date, needs_rebuild, has_live_price_updates, news_refresh: 2,
    )

    def raise_prediction_error(self, *, stock_code: str, latest_trade_date: date) -> object:
        raise RuntimeError("prediction exploded")

    monkeypatch.setattr(
        stock_research_module.StockResearchService,
        "predict_for_refresh",
        raise_prediction_error,
    )

    updated_task = service.run(task.id)
    stage_logs = session.scalars(
        select(StockRefreshStageLog)
        .where(StockRefreshStageLog.task_id == task.id)
        .order_by(StockRefreshStageLog.id.asc())
    ).all()

    assert updated_task.status == "partial"
    assert updated_task.error_message == "prediction exploded"
    assert [log.status for log in stage_logs[:-1]] == ["success"] * 5
    assert stage_logs[-1].stage_name == "prediction"
    assert stage_logs[-1].status == "failed"
    assert stage_logs[-1].error_message == "prediction exploded"

    latest_status = service.latest_status("600010")

    assert latest_status is not None
    assert latest_status["status"] == "partial"
    assert latest_status["error_message"] == "prediction exploded"
    assert latest_status["stages"][-1]["status"] == "failed"
    assert latest_status["stages"][-1]["error_message"] == "prediction exploded"
