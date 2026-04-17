from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin


class MarketScanResult(CreatedAtMixin, Base):
    __tablename__ = "market_scan_result"
    __table_args__ = (
        UniqueConstraint("scan_date", "stock_code", name="uq_market_scan_result_scan_date_stock_code"),
        Index("ix_market_scan_result_scan_date_rank_no", "scan_date", "rank_no"),
        Index("ix_market_scan_result_stock_code_scan_date", "stock_code", "scan_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    scan_date: Mapped[date] = mapped_column(Date(), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    stock_name: Mapped[str | None] = mapped_column(String(64))
    rank_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    rank_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    pattern_score: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    confidence: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    event_density: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False, default=0)
    latest_refresh_at: Mapped[datetime | None] = mapped_column(DateTime())
    source_version: Mapped[str | None] = mapped_column(String(64))


class WatchlistRefreshTask(CreatedAtMixin, Base):
    __tablename__ = "watchlist_refresh_task"
    __table_args__ = (
        Index("ix_watchlist_refresh_task_status_start_time", "status", "start_time"),
        Index(
            "uq_watchlist_refresh_task_inflight_scope_key",
            "scope_key",
            unique=True,
            sqlite_where=text("status IN ('queued', 'running')"),
            postgresql_where=text("status IN ('queued', 'running')"),
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    scope_key: Mapped[str] = mapped_column(String(16), nullable=False, default="global")
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    scan_date: Mapped[date | None] = mapped_column(Date())
    row_count: Mapped[int | None] = mapped_column(Integer())
    start_time: Mapped[datetime | None] = mapped_column(DateTime())
    end_time: Mapped[datetime | None] = mapped_column(DateTime())
    error_message: Mapped[str | None] = mapped_column(Text())
