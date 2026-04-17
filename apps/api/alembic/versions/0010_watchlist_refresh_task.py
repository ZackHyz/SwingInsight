"""Add persistent watchlist refresh task table.

Revision ID: 0010_watchlist_refresh_task
Revises: 0009_market_scan_result
Create Date: 2026-04-17 00:30:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0010_watchlist_refresh_task"
down_revision = "0009_market_scan_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    sqlite_safe_bigint = sa.BigInteger().with_variant(sa.Integer(), "sqlite")

    op.create_table(
        "watchlist_refresh_task",
        sa.Column("id", sqlite_safe_bigint, primary_key=True, autoincrement=True),
        sa.Column("scope_key", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("scan_date", sa.Date(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_watchlist_refresh_task_status_start_time",
        "watchlist_refresh_task",
        ["status", "start_time"],
    )
    op.create_index(
        "uq_watchlist_refresh_task_inflight_scope_key",
        "watchlist_refresh_task",
        ["scope_key"],
        unique=True,
        sqlite_where=sa.text("status IN ('queued', 'running')"),
        postgresql_where=sa.text("status IN ('queued', 'running')"),
    )


def downgrade() -> None:
    op.drop_index("uq_watchlist_refresh_task_inflight_scope_key", table_name="watchlist_refresh_task")
    op.drop_index("ix_watchlist_refresh_task_status_start_time", table_name="watchlist_refresh_task")
    op.drop_table("watchlist_refresh_task")
