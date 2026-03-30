from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Date, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin, TimestampMixin


class SwingSegment(TimestampMixin, Base):
    __tablename__ = "swing_segment"
    __table_args__ = (
        UniqueConstraint("segment_uid"),
        Index("ix_swing_segment_stock_date", "stock_code", "start_date", "end_date"),
        Index("ix_swing_segment_stock_type", "stock_code", "segment_type"),
        Index("ix_swing_segment_final", "stock_code", "is_final"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    segment_uid: Mapped[str] = mapped_column(String(64), nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    start_point_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    end_point_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    start_date: Mapped[date] = mapped_column(Date(), nullable=False)
    end_date: Mapped[date] = mapped_column(Date(), nullable=False)
    start_point_type: Mapped[str] = mapped_column(String(16), nullable=False)
    end_point_type: Mapped[str] = mapped_column(String(16), nullable=False)
    start_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    end_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    pct_change: Mapped[float | None] = mapped_column(Numeric(10, 4))
    duration_days: Mapped[int | None] = mapped_column()
    max_drawdown_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_rebound_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    max_upside_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    avg_daily_change_pct: Mapped[float | None] = mapped_column(Numeric(10, 4))
    segment_type: Mapped[str | None] = mapped_column(String(32))
    trend_direction: Mapped[str | None] = mapped_column(String(16))
    source_version: Mapped[str | None] = mapped_column(String(64))
    is_final: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)


class SegmentFeature(CreatedAtMixin, Base):
    __tablename__ = "segment_feature"
    __table_args__ = (
        UniqueConstraint("segment_id", "feature_name", "version_code"),
        Index("ix_segment_feature_segment_id", "segment_id"),
        Index("ix_segment_feature_stock_code", "stock_code"),
        Index("ix_segment_feature_group_name", "feature_group", "feature_name"),
        Index("ix_segment_feature_version", "version_code"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    feature_group: Mapped[str] = mapped_column(String(32), nullable=False)
    feature_name: Mapped[str] = mapped_column(String(128), nullable=False)
    feature_value_num: Mapped[float | None] = mapped_column(Numeric(20, 6))
    feature_value_text: Mapped[str | None] = mapped_column(String(512))
    feature_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    version_code: Mapped[str | None] = mapped_column(String(64))


class SegmentLabel(CreatedAtMixin, Base):
    __tablename__ = "segment_label"
    __table_args__ = (
        Index("ix_segment_label_segment_id", "segment_id"),
        Index("ix_segment_label_stock_code", "stock_code"),
        Index("ix_segment_label_type_name", "label_type", "label_name"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    label_type: Mapped[str] = mapped_column(String(32), nullable=False)
    label_name: Mapped[str] = mapped_column(String(128), nullable=False)
    label_value: Mapped[str | None] = mapped_column(String(128))
    score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    source_type: Mapped[str] = mapped_column(String(16), nullable=False, default="system")
    version_code: Mapped[str | None] = mapped_column(String(64))
