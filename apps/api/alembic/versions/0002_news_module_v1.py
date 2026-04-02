"""Extend news schema for processed news and point mapping.

Revision ID: 0002_news_module_v1
Revises: 0001_initial_schema
Create Date: 2026-04-02 10:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0002_news_module_v1"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("news_raw", sa.Column("main_news_id", sa.BigInteger(), nullable=True))
    op.add_column("news_raw", sa.Column("raw_json", sa.JSON(), nullable=True))
    op.add_column("news_raw", sa.Column("fetch_time", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "news_raw",
        sa.Column("is_parsed", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "news_raw",
        sa.Column("parse_status", sa.String(length=32), nullable=True, server_default="pending"),
    )

    op.execute("UPDATE news_raw SET fetch_time = created_at WHERE fetch_time IS NULL")
    op.execute("UPDATE news_raw SET parse_status = 'pending' WHERE parse_status IS NULL")

    op.create_index("ix_news_raw_news_uid", "news_raw", ["news_uid"], unique=True)
    op.create_index("ix_news_raw_stock_code_publish_time", "news_raw", ["stock_code", "publish_time"], unique=False)

    op.create_table(
        "news_processed",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("news_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=True),
        sa.Column("clean_title", sa.String(length=512), nullable=True),
        sa.Column("clean_summary", sa.Text(), nullable=True),
        sa.Column("category", sa.String(length=32), nullable=True),
        sa.Column("sub_category", sa.String(length=32), nullable=True),
        sa.Column("sentiment", sa.String(length=16), nullable=True),
        sa.Column("heat_level", sa.String(length=16), nullable=True),
        sa.Column("keyword_list", sa.JSON(), nullable=True),
        sa.Column("tag_list", sa.JSON(), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("duplicate_group_id", sa.String(length=64), nullable=True),
        sa.Column("main_news_id", sa.BigInteger(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("news_id", name="uq_news_processed_news_id"),
    )
    op.create_index("ix_news_processed_news_id", "news_processed", ["news_id"])
    op.create_index("ix_news_processed_stock_code", "news_processed", ["stock_code"])
    op.create_index("ix_news_processed_category", "news_processed", ["category"])
    op.create_index("ix_news_processed_duplicate_group", "news_processed", ["duplicate_group_id"])

    op.create_table(
        "point_news_map",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("point_id", sa.BigInteger(), nullable=False),
        sa.Column("news_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("point_type", sa.String(length=16), nullable=True),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("anchor_date", sa.Date(), nullable=True),
        sa.Column("distance_days", sa.Integer(), nullable=True),
        sa.Column("weight_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "point_id",
            "news_id",
            "relation_type",
            name="uq_point_news_map_point_id_news_id_relation_type",
        ),
    )
    op.create_index("ix_point_news_map_point_id", "point_news_map", ["point_id"])
    op.create_index("ix_point_news_map_news_id", "point_news_map", ["news_id"])
    op.create_index("ix_point_news_map_stock_code", "point_news_map", ["stock_code"])
    op.create_index("ix_point_news_map_relation_type", "point_news_map", ["relation_type"])


def downgrade() -> None:
    op.drop_index("ix_point_news_map_relation_type", table_name="point_news_map")
    op.drop_index("ix_point_news_map_stock_code", table_name="point_news_map")
    op.drop_index("ix_point_news_map_news_id", table_name="point_news_map")
    op.drop_index("ix_point_news_map_point_id", table_name="point_news_map")
    op.drop_table("point_news_map")

    op.drop_index("ix_news_processed_duplicate_group", table_name="news_processed")
    op.drop_index("ix_news_processed_category", table_name="news_processed")
    op.drop_index("ix_news_processed_stock_code", table_name="news_processed")
    op.drop_index("ix_news_processed_news_id", table_name="news_processed")
    op.drop_table("news_processed")

    op.drop_index("ix_news_raw_stock_code_publish_time", table_name="news_raw")
    op.drop_index("ix_news_raw_news_uid", table_name="news_raw")

    op.drop_column("news_raw", "parse_status")
    op.drop_column("news_raw", "is_parsed")
    op.drop_column("news_raw", "fetch_time")
    op.drop_column("news_raw", "raw_json")
    op.drop_column("news_raw", "main_news_id")
