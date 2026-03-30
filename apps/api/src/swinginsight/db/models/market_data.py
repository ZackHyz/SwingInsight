from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin, TimestampMixin


class DailyPrice(TimestampMixin, Base):
    __tablename__ = "daily_price"
    __table_args__ = (
        UniqueConstraint("stock_code", "trade_date", "adj_type"),
        Index("ix_daily_price_stock_code_trade_date", "stock_code", "trade_date"),
        Index("ix_daily_price_trade_date", "trade_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date(), nullable=False)
    open_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    pre_close_price: Mapped[float | None] = mapped_column(Numeric(12, 4))
    change_amount: Mapped[float | None] = mapped_column(Numeric(12, 4))
    change_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    volume: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2))
    amplitude_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    turnover_rate: Mapped[float | None] = mapped_column(Numeric(10, 4))
    adj_type: Mapped[str] = mapped_column(String(16), nullable=False, default="qfq")
    adj_factor: Mapped[float | None] = mapped_column(Numeric(20, 8))
    is_trading_day: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)
    data_source: Mapped[str | None] = mapped_column(String(32))


class TradeRecord(CreatedAtMixin, Base):
    __tablename__ = "trade_record"
    __table_args__ = (
        Index("ix_trade_record_stock_date", "stock_code", "trade_date"),
        Index("ix_trade_record_group_id", "order_group_id"),
        Index("ix_trade_record_strategy_tag", "strategy_tag"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    trade_date: Mapped[date] = mapped_column(Date(), nullable=False)
    trade_time: Mapped[datetime | None] = mapped_column(DateTime())
    trade_type: Mapped[str] = mapped_column(String(16), nullable=False)
    price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    quantity: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    amount: Mapped[float | None] = mapped_column(Numeric(20, 2))
    fee: Mapped[float | None] = mapped_column(Numeric(12, 2), default=0)
    tax: Mapped[float | None] = mapped_column(Numeric(12, 2), default=0)
    account_id: Mapped[str | None] = mapped_column(String(64))
    strategy_tag: Mapped[str | None] = mapped_column(String(64))
    order_group_id: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text())
    source: Mapped[str | None] = mapped_column(String(32))


class AlgoVersion(CreatedAtMixin, Base):
    __tablename__ = "algo_version"
    __table_args__ = (Index("ix_algo_version_algo_type", "algo_type"),)

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    version_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    algo_type: Mapped[str] = mapped_column(String(32), nullable=False)
    version_name: Mapped[str | None] = mapped_column(String(128))
    params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    description: Mapped[str | None] = mapped_column(Text())
    is_active: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=True)


class TaskRunLog(CreatedAtMixin, Base):
    __tablename__ = "task_run_log"
    __table_args__ = (
        Index("ix_task_run_log_task_name", "task_name"),
        Index("ix_task_run_log_target_code", "target_code"),
        Index("ix_task_run_log_status", "status"),
        Index("ix_task_run_log_start_time", "start_time"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    task_name: Mapped[str] = mapped_column(String(128), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_code: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    start_time: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    end_time: Mapped[datetime | None] = mapped_column(DateTime())
    duration_ms: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    input_params_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    result_summary: Mapped[str | None] = mapped_column(Text())
    error_message: Mapped[str | None] = mapped_column(Text())
