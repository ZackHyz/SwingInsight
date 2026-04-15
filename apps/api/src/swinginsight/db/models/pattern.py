from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin, TimestampMixin


class PatternWindow(TimestampMixin, Base):
    __tablename__ = "pattern_window"
    __table_args__ = (
        UniqueConstraint("window_uid"),
        Index("ix_pattern_window_stock_code_start_date_end_date", "stock_code", "start_date", "end_date"),
        Index("ix_pattern_window_segment_id", "segment_id"),
        Index("ix_pattern_window_stock_code_window_size", "stock_code", "window_size"),
        Index("ix_pattern_window_feature_version", "feature_version"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    window_uid: Mapped[str] = mapped_column(String(128), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    segment_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    start_date: Mapped[date] = mapped_column(Date(), nullable=False)
    end_date: Mapped[date] = mapped_column(Date(), nullable=False)
    window_size: Mapped[int] = mapped_column(Integer(), nullable=False)
    start_close: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    end_close: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    period_pct_change: Mapped[float | None] = mapped_column(Numeric(10, 4))
    highest_day_pos: Mapped[int | None] = mapped_column(Integer())
    lowest_day_pos: Mapped[int | None] = mapped_column(Integer())
    trend_label: Mapped[str | None] = mapped_column(String(32))
    feature_version: Mapped[str | None] = mapped_column(String(64))


class PatternFeature(CreatedAtMixin, Base):
    __tablename__ = "pattern_feature"
    __table_args__ = (
        UniqueConstraint("window_id"),
        Index("ix_pattern_feature_window_id", "window_id"),
        Index("ix_pattern_feature_feature_version", "feature_version"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    window_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    price_seq_json: Mapped[list[float] | None] = mapped_column(JSON)
    return_seq_json: Mapped[list[float] | None] = mapped_column(JSON)
    candle_feat_json: Mapped[list[float] | None] = mapped_column(JSON)
    volume_seq_json: Mapped[list[float] | None] = mapped_column(JSON)
    turnover_seq_json: Mapped[list[float] | None] = mapped_column(JSON)
    trend_context_json: Mapped[list[float] | None] = mapped_column(JSON)
    vola_context_json: Mapped[list[float] | None] = mapped_column(JSON)
    coarse_vector_json: Mapped[list[float] | None] = mapped_column(JSON)
    context_feature_json: Mapped[dict[str, float] | None] = mapped_column(JSON)
    feature_version: Mapped[str | None] = mapped_column(String(64))


class PatternFutureStat(CreatedAtMixin, Base):
    __tablename__ = "pattern_future_stat"
    __table_args__ = (
        UniqueConstraint("window_id"),
        Index("ix_pattern_future_stat_window_id", "window_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    window_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    ret_1d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    ret_3d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    ret_5d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    ret_10d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_up_3d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_dd_3d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_up_5d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_dd_5d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_up_10d: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_dd_10d: Mapped[float | None] = mapped_column(Numeric(10, 4))


class PatternMatchResult(CreatedAtMixin, Base):
    __tablename__ = "pattern_match_result"
    __table_args__ = (
        UniqueConstraint("query_signature", "target_window_id"),
        Index("ix_pattern_match_result_query_signature_rank_no", "query_signature", "rank_no"),
        Index("ix_pattern_match_result_query_window_id", "query_window_id"),
        Index("ix_pattern_match_result_target_window_id", "target_window_id"),
        Index("ix_pattern_match_result_feature_version", "feature_version"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    query_signature: Mapped[str] = mapped_column(String(128), nullable=False)
    query_window_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    target_window_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    rank_no: Mapped[int] = mapped_column(Integer(), nullable=False)
    total_similarity: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sim_price: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sim_candle: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sim_volume: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sim_turnover: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sim_trend: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sim_vola: Mapped[float | None] = mapped_column(Numeric(8, 4))
    feature_version: Mapped[str | None] = mapped_column(String(64))
