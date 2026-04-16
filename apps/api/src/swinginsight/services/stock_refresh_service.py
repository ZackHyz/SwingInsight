from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any, Callable

from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from swinginsight.db.models.refresh import StockRefreshStageLog, StockRefreshTask
from swinginsight.jobs.align_news import AlignNewsResult
from swinginsight.jobs.process_news import ProcessNewsResult
from swinginsight.services.stock_research_service import NewsRefreshResult, PriceRefreshResult, StockResearchService


@dataclass(slots=True)
class StageExecutionResult:
    value: Any = None
    status: str = "success"
    source: str | None = None
    rows_changed: int | None = 0


class StockRefreshService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(self, stock_code: str) -> StockRefreshTask:
        existing = self._latest_inflight_task(stock_code)
        if existing is not None:
            return existing

        task = StockRefreshTask(
            stock_code=stock_code,
            status="queued",
        )
        self.session.add(task)
        try:
            self.session.commit()
        except IntegrityError:
            self.session.rollback()
            existing = self._latest_inflight_task(stock_code)
            if existing is not None:
                return existing
            raise
        self.session.refresh(task)
        return task

    def run(self, task_id: int) -> StockRefreshTask:
        task = self.session.get(StockRefreshTask, task_id)
        if task is None:
            raise ValueError(f"refresh task {task_id} not found")
        if task.status == "running":
            return task
        if task.status not in {"queued", "failed", "partial"}:
            return task

        research = StockResearchService(self.session)
        preparation = research.prepare_refresh(task.stock_code)

        task.status = "running"
        task.start_time = _utcnow()
        task.end_time = None
        task.error_message = None
        self.session.execute(delete(StockRefreshStageLog).where(StockRefreshStageLog.task_id == task.id))
        self.session.commit()

        completed_stage_count = 0
        latest_trade_date = preparation.latest_trade_date_before_refresh
        news_refresh = NewsRefreshResult(
            start_date=latest_trade_date or date.today(),
            end_date=latest_trade_date or date.today(),
            inserted=0,
            processed_count=0,
            duplicates=0,
            point_mappings=0,
            segment_mappings=0,
        )

        try:
            price_refresh = self._execute_stage(
                task=task,
                stage_name="price_import",
                callback=lambda: self._run_price_stage(
                    research=research,
                    stock_code=task.stock_code,
                    latest_trade_date_before_refresh=preparation.latest_trade_date_before_refresh,
                    should_refresh_remote=preparation.should_refresh_remote,
                ),
            )
            completed_stage_count += 1

            latest_trade_date = research.load_latest_trade_date(task.stock_code)
            if latest_trade_date is None:
                raise RuntimeError(f"no price data available for {task.stock_code}")
            needs_rebuild = research.needs_rebuild(stock_code=task.stock_code, latest_trade_date=latest_trade_date)
            has_live_price_updates = price_refresh.inserted > 0 or price_refresh.updated > 0

            window_start, window_end = research.resolve_news_window(anchor_date=latest_trade_date)

            news_import_count = self._execute_stage(
                task=task,
                stage_name="news_import",
                callback=lambda: self._run_news_import_stage(
                    research=research,
                    stock_code=task.stock_code,
                    start_date=window_start,
                    end_date=window_end,
                    should_refresh_remote=preparation.should_refresh_remote,
                ),
            )
            completed_stage_count += 1

            process_result = self._execute_stage(
                task=task,
                stage_name="news_process",
                callback=lambda: self._run_news_process_stage(
                    research=research,
                    stock_code=task.stock_code,
                    start_date=window_start,
                    end_date=window_end,
                    should_refresh_remote=preparation.should_refresh_remote,
                ),
            )
            completed_stage_count += 1

            align_result = self._execute_stage(
                task=task,
                stage_name="news_align",
                callback=lambda: self._run_news_align_stage(
                    research=research,
                    stock_code=task.stock_code,
                    start_date=window_start,
                    end_date=window_end,
                    should_refresh_remote=preparation.should_refresh_remote,
                ),
            )
            completed_stage_count += 1

            news_refresh = NewsRefreshResult(
                start_date=window_start,
                end_date=window_end,
                inserted=news_import_count,
                processed_count=process_result.processed_count,
                duplicates=process_result.duplicates,
                point_mappings=align_result.point_mappings,
                segment_mappings=align_result.segment_mappings,
            )

            materialized_count = self._execute_stage(
                task=task,
                stage_name="pattern_materialize",
                callback=lambda: self._run_pattern_materialize_stage(
                    research=research,
                    stock_code=task.stock_code,
                    latest_trade_date=latest_trade_date,
                    needs_rebuild=needs_rebuild,
                    has_live_price_updates=has_live_price_updates,
                    news_refresh=news_refresh,
                ),
            )
            completed_stage_count += 1

            self._execute_stage(
                task=task,
                stage_name="prediction",
                callback=lambda: self._run_prediction_stage(
                    research=research,
                    stock_code=task.stock_code,
                    latest_trade_date=latest_trade_date,
                    prediction_required=materialized_count > 0,
                ),
            )
            completed_stage_count += 1

            if not research.stock_exists(task.stock_code):
                raise RuntimeError(f"stock {task.stock_code} missing after refresh")

        except Exception as exc:
            task.status = "partial" if completed_stage_count > 0 else "failed"
            task.end_time = _utcnow()
            task.error_message = str(exc)
            self.session.commit()
            self.session.refresh(task)
            return task

        task.status = "success"
        task.end_time = _utcnow()
        task.error_message = None
        self.session.commit()
        self.session.refresh(task)
        return task

    def latest_status(self, stock_code: str) -> dict[str, object] | None:
        task = self.session.scalar(
            select(StockRefreshTask)
            .where(StockRefreshTask.stock_code == stock_code)
            .order_by(StockRefreshTask.created_at.desc(), StockRefreshTask.id.desc())
            .limit(1)
        )
        if task is None:
            return None

        stage_logs = self.session.scalars(
            select(StockRefreshStageLog)
            .where(StockRefreshStageLog.task_id == task.id)
            .order_by(StockRefreshStageLog.id.asc())
        ).all()
        return {
            "task_id": task.id,
            "stock_code": task.stock_code,
            "status": task.status,
            "created_at": _serialize_datetime(task.created_at),
            "start_time": _serialize_datetime(task.start_time),
            "end_time": _serialize_datetime(task.end_time),
            "error_message": task.error_message,
            "stages": [
                {
                    "stage_name": stage_log.stage_name,
                    "status": stage_log.status,
                    "source": stage_log.source,
                    "rows_changed": stage_log.rows_changed,
                    "start_time": _serialize_datetime(stage_log.start_time),
                    "end_time": _serialize_datetime(stage_log.end_time),
                    "duration_ms": stage_log.duration_ms,
                    "error_message": stage_log.error_message,
                }
                for stage_log in stage_logs
            ],
        }

    def _latest_inflight_task(self, stock_code: str) -> StockRefreshTask | None:
        return self.session.scalar(
            select(StockRefreshTask)
            .where(
                StockRefreshTask.stock_code == stock_code,
                StockRefreshTask.status.in_(("queued", "running")),
            )
            .order_by(StockRefreshTask.created_at.desc(), StockRefreshTask.id.desc())
            .limit(1)
        )

    def _execute_stage(
        self,
        *,
        task: StockRefreshTask,
        stage_name: str,
        callback: Callable[[], StageExecutionResult],
    ) -> Any:
        start_time = _utcnow()
        try:
            result = callback()
        except Exception as exc:
            self.session.rollback()
            end_time = _utcnow()
            self.session.add(
                StockRefreshStageLog(
                    task_id=task.id,
                    stage_name=stage_name,
                    status="failed",
                    start_time=start_time,
                    end_time=end_time,
                    duration_ms=_duration_ms(start_time, end_time),
                    error_message=str(exc),
                )
            )
            self.session.commit()
            raise

        end_time = _utcnow()
        self.session.add(
            StockRefreshStageLog(
                task_id=task.id,
                stage_name=stage_name,
                status=result.status,
                source=result.source,
                rows_changed=result.rows_changed,
                start_time=start_time,
                end_time=end_time,
                duration_ms=_duration_ms(start_time, end_time),
            )
        )
        self.session.commit()
        return result.value

    def _run_price_stage(
        self,
        *,
        research: StockResearchService,
        stock_code: str,
        latest_trade_date_before_refresh: date | None,
        should_refresh_remote: bool,
    ) -> StageExecutionResult:
        if not should_refresh_remote:
            return StageExecutionResult(
                value=PriceRefreshResult(source="local_cache", inserted=0, updated=0, skipped=1),
                status="skipped",
                source="local_cache",
                rows_changed=0,
            )

        result = research.refresh_live_prices(stock_code, latest_trade_date_before_refresh)
        return StageExecutionResult(
            value=result,
            source=result.source,
            rows_changed=result.inserted + result.updated,
        )

    def _run_news_import_stage(
        self,
        *,
        research: StockResearchService,
        stock_code: str,
        start_date: date,
        end_date: date,
        should_refresh_remote: bool,
    ) -> StageExecutionResult:
        if not should_refresh_remote:
            return StageExecutionResult(status="skipped", source="local_cache", rows_changed=0, value=0)

        inserted = research.import_news_window(stock_code, start_date=start_date, end_date=end_date)
        return StageExecutionResult(
            value=inserted,
            source="news_pipeline",
            rows_changed=inserted,
        )

    def _run_news_process_stage(
        self,
        *,
        research: StockResearchService,
        stock_code: str,
        start_date: date,
        end_date: date,
        should_refresh_remote: bool,
    ) -> StageExecutionResult:
        if not should_refresh_remote:
            return StageExecutionResult(
                status="skipped",
                source="local_cache",
                rows_changed=0,
                value=ProcessNewsResult(processed_count=0, duplicates=0),
            )

        result = research.process_news_window(stock_code, start_date=start_date, end_date=end_date)
        return StageExecutionResult(
            value=result,
            source="news_pipeline",
            rows_changed=result.processed_count,
        )

    def _run_news_align_stage(
        self,
        *,
        research: StockResearchService,
        stock_code: str,
        start_date: date,
        end_date: date,
        should_refresh_remote: bool,
    ) -> StageExecutionResult:
        if not should_refresh_remote:
            return StageExecutionResult(
                status="skipped",
                source="local_cache",
                rows_changed=0,
                value=AlignNewsResult(point_mappings=0, segment_mappings=0),
            )

        result = research.align_news_window(stock_code, start_date=start_date, end_date=end_date)
        return StageExecutionResult(
            value=result,
            source="news_pipeline",
            rows_changed=result.point_mappings + result.segment_mappings,
        )

    def _run_pattern_materialize_stage(
        self,
        *,
        research: StockResearchService,
        stock_code: str,
        latest_trade_date: date,
        needs_rebuild: bool,
        has_live_price_updates: bool,
        news_refresh: NewsRefreshResult,
    ) -> StageExecutionResult:
        materialized_count = research.materialize_refresh_artifacts(
            stock_code=stock_code,
            latest_trade_date=latest_trade_date,
            needs_rebuild=needs_rebuild,
            has_live_price_updates=has_live_price_updates,
            news_refresh=news_refresh,
        )
        return StageExecutionResult(
            value=materialized_count,
            source="research_pipeline",
            rows_changed=materialized_count,
        )

    def _run_prediction_stage(
        self,
        *,
        research: StockResearchService,
        stock_code: str,
        latest_trade_date: date,
        prediction_required: bool,
    ) -> StageExecutionResult:
        if not prediction_required:
            return StageExecutionResult(status="skipped", source="prediction_service", rows_changed=0)

        research.predict_for_refresh(stock_code=stock_code, latest_trade_date=latest_trade_date)
        return StageExecutionResult(
            source="prediction_service",
            rows_changed=1,
        )


def _duration_ms(start_time: datetime, end_time: datetime) -> int:
    return int((end_time - start_time).total_seconds() * 1000)


def _serialize_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _utcnow() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)
