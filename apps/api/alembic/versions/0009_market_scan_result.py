"""Add market scan result table for ranked watchlist.

Revision ID: 0009_market_scan_result
Revises: 0008_refresh_task
Create Date: 2026-04-17 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_market_scan_result"
down_revision = "0008_refresh_task"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sqlite_safe_bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

    op.create_table(
        "market_scan_result",
        sa.Column("id", sqlite_safe_bigint, primary_key=True, autoincrement=True),
        sa.Column("scan_date", sa.Date(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("stock_name", sa.String(length=64), nullable=True),
        sa.Column("rank_no", sa.Integer(), nullable=False),
        sa.Column("rank_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("pattern_score", sa.Numeric(8, 4), nullable=False),
        sa.Column("confidence", sa.Numeric(8, 4), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("event_density", sa.Numeric(8, 4), nullable=False),
        sa.Column("latest_refresh_at", sa.DateTime(), nullable=True),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("scan_date", "stock_code", name="uq_market_scan_result_scan_date_stock_code"),
    )
    op.create_index(
        "ix_market_scan_result_scan_date_rank_no",
        "market_scan_result",
        ["scan_date", "rank_no"],
    )
    op.create_index(
        "ix_market_scan_result_stock_code_scan_date",
        "market_scan_result",
        ["stock_code", "scan_date"],
    )


def downgrade() -> None:
    op.drop_index("ix_market_scan_result_stock_code_scan_date", table_name="market_scan_result")
    op.drop_index("ix_market_scan_result_scan_date_rank_no", table_name="market_scan_result")
    op.drop_table("market_scan_result")
