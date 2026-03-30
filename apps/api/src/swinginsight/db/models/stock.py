from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, TimestampMixin


class StockBasic(TimestampMixin, Base):
    __tablename__ = "stock_basic"

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    stock_code: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)
    stock_name: Mapped[str] = mapped_column(String(128), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False, default="A")
    industry: Mapped[str | None] = mapped_column(String(128))
    concept_tags: Mapped[list[Any] | None] = mapped_column(JSON)
