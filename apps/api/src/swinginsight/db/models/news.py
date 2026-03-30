from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Index, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin


class NewsRaw(CreatedAtMixin, Base):
    __tablename__ = "news_raw"
    __table_args__ = (
        Index("ix_news_raw_stock_code", "stock_code"),
        Index("ix_news_raw_publish_time", "publish_time"),
        Index("ix_news_raw_news_date", "news_date"),
        Index("ix_news_raw_news_type", "news_type"),
        Index("ix_news_raw_duplicate_group", "duplicate_group_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    news_uid: Mapped[str | None] = mapped_column(String(128))
    stock_code: Mapped[str | None] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text())
    content: Mapped[str | None] = mapped_column(Text())
    publish_time: Mapped[datetime] = mapped_column(DateTime(), nullable=False)
    news_date: Mapped[date | None] = mapped_column(Date())
    source_name: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str | None] = mapped_column(String(32))
    url: Mapped[str | None] = mapped_column(Text())
    related_industry: Mapped[str | None] = mapped_column(String(128))
    related_concept: Mapped[str | None] = mapped_column(String(128))
    sentiment: Mapped[str | None] = mapped_column(String(16))
    news_type: Mapped[str | None] = mapped_column(String(32))
    keywords: Mapped[str | None] = mapped_column(Text())
    is_duplicate: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64))
    data_source: Mapped[str | None] = mapped_column(String(32))


class SegmentNewsMap(CreatedAtMixin, Base):
    __tablename__ = "segment_news_map"
    __table_args__ = (
        UniqueConstraint("segment_id", "news_id", "relation_type"),
        Index("ix_segment_news_map_segment_id", "segment_id"),
        Index("ix_segment_news_map_news_id", "news_id"),
        Index("ix_segment_news_map_stock_code", "stock_code"),
        Index("ix_segment_news_map_relation_type", "relation_type"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    segment_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    news_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    window_type: Mapped[str | None] = mapped_column(String(32))
    anchor_date: Mapped[date | None] = mapped_column(Date())
    distance_days: Mapped[int | None] = mapped_column()
    weight_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
