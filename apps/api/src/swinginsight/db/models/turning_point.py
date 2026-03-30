from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Date, Index, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin, TimestampMixin


class TurningPoint(TimestampMixin, Base):
    __tablename__ = "turning_point"
    __table_args__ = (
        Index("ix_turning_point_stock_date", "stock_code", "point_date"),
        Index("ix_turning_point_stock_type", "stock_code", "point_type"),
        Index("ix_turning_point_final", "stock_code", "is_final"),
        Index("ix_turning_point_version", "version_code"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    point_date: Mapped[date] = mapped_column(Date(), nullable=False)
    point_type: Mapped[str] = mapped_column(String(16), nullable=False)
    point_price: Mapped[float] = mapped_column(Numeric(12, 4), nullable=False)
    confirm_date: Mapped[date | None] = mapped_column(Date())
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)
    version_code: Mapped[str | None] = mapped_column(String(64))
    parent_point_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    is_final: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    confidence_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    remark: Mapped[str | None] = mapped_column(Text())
    created_by: Mapped[str | None] = mapped_column(String(64))


class PointRevisionLog(CreatedAtMixin, Base):
    __tablename__ = "point_revision_log"
    __table_args__ = (
        Index("ix_point_revision_log_stock_code", "stock_code"),
        Index("ix_point_revision_log_point_id", "point_id"),
        Index("ix_point_revision_log_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    point_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    operation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    old_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    new_value_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    operator: Mapped[str | None] = mapped_column(String(64))
    remark: Mapped[str | None] = mapped_column(Text())
