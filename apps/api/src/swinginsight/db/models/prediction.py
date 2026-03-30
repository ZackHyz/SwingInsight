from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin


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
