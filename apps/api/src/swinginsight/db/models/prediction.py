from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin, TimestampMixin


class PredictionResult(CreatedAtMixin, Base):
    __tablename__ = "prediction_result"
    __table_args__ = (
        UniqueConstraint("stock_code", "predict_date", "model_version"),
        Index("ix_prediction_result_stock_date", "stock_code", "predict_date"),
        Index("ix_prediction_result_state", "current_state"),
        Index("ix_prediction_result_model_version", "model_version"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    predict_date: Mapped[date] = mapped_column(Date(), nullable=False)
    current_state: Mapped[str] = mapped_column(String(64), nullable=False)
    up_prob_5d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    flat_prob_5d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    down_prob_5d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    up_prob_10d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    flat_prob_10d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    down_prob_10d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    up_prob_20d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    flat_prob_20d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    down_prob_20d: Mapped[float | None] = mapped_column(Numeric(8, 4))
    similarity_topn_json: Mapped[list[Any] | None] = mapped_column(JSON)
    key_features_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    risk_flags_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text())


class ScoreLog(TimestampMixin, Base):
    __tablename__ = "score_log"
    __table_args__ = (
        Index("ix_score_log_stock_code_query_end_date", "stock_code", "query_end_date"),
        Index("ix_score_log_query_window_id", "query_window_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    query_window_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    query_end_date: Mapped[date] = mapped_column(Date(), nullable=False)
    predicted_win_rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    predicted_avg_return: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    sample_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    actual_return_5d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    actual_return_10d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    actual_outcome_5d: Mapped[int | None] = mapped_column(Integer())
    actual_outcome_10d: Mapped[int | None] = mapped_column(Integer())


class BacktestResult(CreatedAtMixin, Base):
    __tablename__ = "backtest_result"
    __table_args__ = (
        UniqueConstraint("stock_code", "window_id", "horizon_days"),
        Index("ix_backtest_result_stock_code_horizon_days", "stock_code", "horizon_days"),
        Index("ix_backtest_result_query_start_date", "query_start_date"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    window_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    horizon_days: Mapped[int] = mapped_column(Integer(), nullable=False)
    query_start_date: Mapped[date] = mapped_column(Date(), nullable=False)
    query_end_date: Mapped[date] = mapped_column(Date(), nullable=False)
    ref_latest_end_date: Mapped[date | None] = mapped_column(Date())
    predicted_win_rate: Mapped[float] = mapped_column(Numeric(8, 4), nullable=False)
    predicted_avg_return: Mapped[float] = mapped_column(Numeric(10, 4), nullable=False)
    actual_return: Mapped[float | None] = mapped_column(Numeric(10, 4))
    actual_outcome: Mapped[int | None] = mapped_column(Integer())
    sample_count: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
