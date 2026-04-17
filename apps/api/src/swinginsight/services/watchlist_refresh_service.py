from __future__ import annotations

from datetime import UTC, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from swinginsight.db.models.watchlist import WatchlistRefreshTask
from swinginsight.services.market_watchlist_service import MarketWatchlistService

RUNNING_TASK_STALE_TIMEOUT = timedelta(minutes=30)
WATCHLIST_SCOPE_KEY = "global"


class WatchlistRefreshService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def enqueue(self) -> WatchlistRefreshTask:
        for _ in range(3):
            existing = self._latest_inflight_task()
            if existing is not None:
                if self._expire_stale_running_task(existing):
                    continue
                return existing

            task = WatchlistRefreshTask(
                scope_key=WATCHLIST_SCOPE_KEY,
                status="queued",
            )
            self.session.add(task)
            try:
                self.session.commit()
            except IntegrityError:
                self.session.rollback()
                continue
            self.session.refresh(task)
            return task

        raise RuntimeError("unable to enqueue watchlist refresh task")

    def run(self, task_id: int, *, limit: int = 30) -> WatchlistRefreshTask:
        task = self.session.get(WatchlistRefreshTask, task_id)
        if task is None:
            raise ValueError(f"watchlist refresh task {task_id} not found")
        if task.status == "running":
            return task
        if task.status not in {"queued", "failed"}:
            return task

        task.status = "running"
        task.start_time = _utcnow()
        task.end_time = None
        task.error_message = None
        task.scan_date = None
        task.row_count = None
        self.session.commit()

        try:
            payload = MarketWatchlistService(self.session).refresh_watchlist(limit=limit)
        except Exception as exc:
            task.status = "failed"
            task.end_time = _utcnow()
            task.error_message = str(exc)
            self.session.commit()
            self.session.refresh(task)
            return task

        scan_date = payload.get("scan_date")
        rows = payload.get("rows", [])
        task.status = "success"
        task.scan_date = _parse_scan_date(scan_date)
        task.row_count = len(rows)
        task.end_time = _utcnow()
        task.error_message = None
        self.session.commit()
        self.session.refresh(task)
        return task

    def latest_status(self) -> dict[str, object] | None:
        task = self.session.scalar(
            select(WatchlistRefreshTask)
            .order_by(WatchlistRefreshTask.created_at.desc(), WatchlistRefreshTask.id.desc())
            .limit(1)
        )
        if task is None:
            return None
        return self._serialize_task(task)

    def _latest_inflight_task(self) -> WatchlistRefreshTask | None:
        return self.session.scalar(
            select(WatchlistRefreshTask)
            .where(
                WatchlistRefreshTask.scope_key == WATCHLIST_SCOPE_KEY,
                WatchlistRefreshTask.status.in_(("queued", "running")),
            )
            .order_by(WatchlistRefreshTask.created_at.desc(), WatchlistRefreshTask.id.desc())
            .limit(1)
        )

    def _expire_stale_running_task(self, task: WatchlistRefreshTask) -> bool:
        if not self._is_stale_running_task(task):
            return False

        task.status = "failed"
        task.end_time = _utcnow()
        task.error_message = "stale_running_timeout"
        self.session.commit()
        self.session.refresh(task)
        return True

    def _is_stale_running_task(self, task: WatchlistRefreshTask) -> bool:
        if task.status != "running" or task.end_time is not None or task.start_time is None:
            return False
        return _utcnow() - task.start_time.replace(tzinfo=UTC) > RUNNING_TASK_STALE_TIMEOUT

    def _serialize_task(self, task: WatchlistRefreshTask) -> dict[str, object]:
        return {
            "task_id": task.id,
            "status": task.status,
            "created_at": _serialize_datetime(task.created_at),
            "start_time": _serialize_datetime(task.start_time),
            "end_time": _serialize_datetime(task.end_time),
            "updated_at": _serialize_datetime(task.end_time or task.start_time or task.created_at),
            "error_message": task.error_message,
            "scan_date": task.scan_date.isoformat() if task.scan_date is not None else None,
            "row_count": task.row_count,
        }


def _serialize_datetime(value):
    return value.isoformat() if value is not None else None


def _utcnow():
    from datetime import datetime

    return datetime.now(UTC)


def _parse_scan_date(value):
    if value in {None, ""}:
        return None
    from datetime import date

    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
