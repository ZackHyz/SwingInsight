"""Add stock refresh task and stage log tables.

Revision ID: 0008_refresh_task
Revises: 0007_pattern_context_features
Create Date: 2026-04-16 00:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_refresh_task"
down_revision = "0007_pattern_context_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_refresh_task",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_stock_refresh_task_stock_code_status_start_time",
        "stock_refresh_task",
        ["stock_code", "status", "start_time"],
    )
    op.create_index(
        "uq_stock_refresh_task_inflight_stock_code",
        "stock_refresh_task",
        ["stock_code"],
        unique=True,
        postgresql_where=sa.text("status IN ('queued', 'running')"),
        sqlite_where=sa.text("status IN ('queued', 'running')"),
    )

    op.create_table(
        "stock_refresh_stage_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("task_id", sa.BigInteger(), sa.ForeignKey("stock_refresh_task.id"), nullable=False),
        sa.Column("stage_name", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("rows_changed", sa.Integer(), nullable=True),
        sa.Column("start_time", sa.DateTime(), nullable=True),
        sa.Column("end_time", sa.DateTime(), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_stock_refresh_stage_log_task_id_stage_name",
        "stock_refresh_stage_log",
        ["task_id", "stage_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_stock_refresh_stage_log_task_id_stage_name", table_name="stock_refresh_stage_log")
    op.drop_table("stock_refresh_stage_log")
    op.drop_index("uq_stock_refresh_task_inflight_stock_code", table_name="stock_refresh_task")
    op.drop_index("ix_stock_refresh_task_stock_code_status_start_time", table_name="stock_refresh_task")
    op.drop_table("stock_refresh_task")
