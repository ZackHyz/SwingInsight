from __future__ import annotations

from datetime import date, datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, DateTime, Index, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from swinginsight.db.base import BIGINT_TYPE, Base, CreatedAtMixin


class NewsRaw(CreatedAtMixin, Base):
    __tablename__ = "news_raw"
    __table_args__ = (
        Index("ix_news_raw_news_uid", "news_uid", unique=True),
        Index("ix_news_raw_stock_code", "stock_code"),
        Index("ix_news_raw_publish_time", "publish_time"),
        Index("ix_news_raw_stock_code_publish_time", "stock_code", "publish_time"),
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
    main_news_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    raw_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    fetch_time: Mapped[datetime | None] = mapped_column(DateTime())
    is_parsed: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    parse_status: Mapped[str | None] = mapped_column(String(32), default="pending")
    data_source: Mapped[str | None] = mapped_column(String(32))


class NewsProcessed(CreatedAtMixin, Base):
    __tablename__ = "news_processed"
    __table_args__ = (
        UniqueConstraint("news_id"),
        Index("ix_news_processed_news_id", "news_id"),
        Index("ix_news_processed_stock_code", "stock_code"),
        Index("ix_news_processed_category", "category"),
        Index("ix_news_processed_duplicate_group", "duplicate_group_id"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(16))
    clean_title: Mapped[str | None] = mapped_column(String(512))
    clean_summary: Mapped[str | None] = mapped_column(Text())
    category: Mapped[str | None] = mapped_column(String(32))
    sub_category: Mapped[str | None] = mapped_column(String(32))
    sentiment: Mapped[str | None] = mapped_column(String(16))
    heat_level: Mapped[str | None] = mapped_column(String(16))
    keyword_list: Mapped[list[str] | None] = mapped_column(JSON)
    tag_list: Mapped[list[str] | None] = mapped_column(JSON)
    is_duplicate: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    duplicate_group_id: Mapped[str | None] = mapped_column(String(64))
    main_news_id: Mapped[int | None] = mapped_column(BIGINT_TYPE)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime())


class NewsSentimentResult(CreatedAtMixin, Base):
    __tablename__ = "news_sentiment_result"
    __table_args__ = (
        UniqueConstraint("news_id"),
        Index("ix_news_sentiment_result_news_id", "news_id"),
        Index("ix_news_sentiment_result_stock_code", "stock_code"),
        Index("ix_news_sentiment_result_sentiment_label", "sentiment_label"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(16))
    sentiment_label: Mapped[str | None] = mapped_column(String(16))
    sentiment_score_base: Mapped[float | None] = mapped_column(Numeric(8, 4))
    sentiment_score_adjusted: Mapped[float | None] = mapped_column(Numeric(8, 4))
    confidence_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    heat_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    market_context_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    position_context_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
    event_conflict_flag: Mapped[bool] = mapped_column(Boolean(), nullable=False, default=False)
    model_version: Mapped[str | None] = mapped_column(String(64))
    calculated_at: Mapped[datetime | None] = mapped_column(DateTime())


class NewsEventResult(CreatedAtMixin, Base):
    __tablename__ = "news_event_result"
    __table_args__ = (
        UniqueConstraint("news_id", "sentence_index", "event_type"),
        Index("ix_news_event_result_news_id", "news_id"),
        Index("ix_news_event_result_stock_code", "stock_code"),
        Index("ix_news_event_result_event_type", "event_type"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    news_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str | None] = mapped_column(String(16))
    sentence_index: Mapped[int] = mapped_column(Integer(), nullable=False, default=0)
    sentence_text: Mapped[str | None] = mapped_column(Text())
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    event_polarity: Mapped[str | None] = mapped_column(String(16))
    event_strength: Mapped[int | None] = mapped_column(Integer())
    entity_main: Mapped[str | None] = mapped_column(String(128))
    entity_secondary: Mapped[str | None] = mapped_column(String(128))
    trigger_keywords: Mapped[list[str] | None] = mapped_column(JSON)
    model_version: Mapped[str | None] = mapped_column(String(64))


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


class PointNewsMap(CreatedAtMixin, Base):
    __tablename__ = "point_news_map"
    __table_args__ = (
        UniqueConstraint("point_id", "news_id", "relation_type"),
        Index("ix_point_news_map_point_id", "point_id"),
        Index("ix_point_news_map_news_id", "news_id"),
        Index("ix_point_news_map_stock_code", "stock_code"),
        Index("ix_point_news_map_relation_type", "relation_type"),
    )

    id: Mapped[int] = mapped_column(BIGINT_TYPE, primary_key=True, autoincrement=True)
    point_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    news_id: Mapped[int] = mapped_column(BIGINT_TYPE, nullable=False)
    stock_code: Mapped[str] = mapped_column(String(16), nullable=False)
    point_type: Mapped[str | None] = mapped_column(String(16))
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    anchor_date: Mapped[date | None] = mapped_column(Date())
    distance_days: Mapped[int | None] = mapped_column()
    weight_score: Mapped[float | None] = mapped_column(Numeric(8, 4))
