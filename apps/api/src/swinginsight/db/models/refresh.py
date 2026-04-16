from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin


class StockRefreshTask(CreatedAtMixin, Base):
    __tablename__ = "stock_refresh_task"
    __table_args__ = (
        Index("ix_stock_refresh_task_stock_code_status_start_time", "stock_code", "status", "start_time"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime())
    end_time: Mapped[datetime | None] = mapped_column(DateTime())
    error_message: Mapped[str | None] = mapped_column(Text())


class StockRefreshStageLog(CreatedAtMixin, Base):
    __tablename__ = "stock_refresh_stage_log"
    __table_args__ = (
        Index("ix_stock_refresh_stage_log_task_id_stage_name", "task_id", "stage_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    task_id: Mapped[int] = mapped_column(
        BIGINT_TYPE,
        ForeignKey("stock_refresh_task.id"),
        nullable=False,
    )
    stage_name: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    source: Mapped[str | None] = mapped_column(String(32))
    rows_changed: Mapped[int | None] = mapped_column(Integer())
    start_time: Mapped[datetime | None] = mapped_column(DateTime())
    end_time: Mapped[datetime | None] = mapped_column(DateTime())
    duration_ms: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    error_message: Mapped[str | None] = mapped_column(Text())
