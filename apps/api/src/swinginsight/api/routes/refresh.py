from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.refresh import StockRefreshTask
from swinginsight.services.stock_refresh_service import StockRefreshService


def enqueue_stock_refresh(session: Session, stock_code: str) -> dict[str, object]:
    existing_task = session.scalar(
        select(StockRefreshTask)
        .where(
            StockRefreshTask.stock_code == stock_code,
            StockRefreshTask.status.in_(("queued", "running")),
        )
        .order_by(StockRefreshTask.created_at.desc(), StockRefreshTask.id.desc())
        .limit(1)
    )
    task = StockRefreshService(session).enqueue(stock_code)
    return {
        "task_id": task.id,
        "stock_code": task.stock_code,
        "status": task.status,
        "created_at": task.created_at.isoformat(),
        "reused": existing_task is not None and existing_task.id == task.id,
    }


def get_stock_refresh_status(session: Session, stock_code: str) -> dict[str, object] | None:
    return StockRefreshService(session).latest_status(stock_code)
