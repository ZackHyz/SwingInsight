"""Add pattern score backtest result table.

Revision ID: 0006_backtest_result
Revises: 0005_score_validation_log
Create Date: 2026-04-11 16:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_backtest_result"
down_revision = "0005_score_validation_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "backtest_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("window_id", sa.BigInteger(), nullable=False),
        sa.Column("horizon_days", sa.Integer(), nullable=False),
        sa.Column("query_start_date", sa.Date(), nullable=False),
        sa.Column("query_end_date", sa.Date(), nullable=False),
        sa.Column("ref_latest_end_date", sa.Date(), nullable=True),
        sa.Column("predicted_win_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("predicted_avg_return", sa.Numeric(10, 4), nullable=False),
        sa.Column("actual_return", sa.Numeric(10, 4), nullable=True),
        sa.Column("actual_outcome", sa.Integer(), nullable=True),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stock_code", "window_id", "horizon_days", name="uq_backtest_result_stock_code_window_id_horizon_days"),
    )
    op.create_index("ix_backtest_result_stock_code_horizon_days", "backtest_result", ["stock_code", "horizon_days"])
    op.create_index("ix_backtest_result_query_start_date", "backtest_result", ["query_start_date"])


def downgrade() -> None:
    op.drop_index("ix_backtest_result_query_start_date", table_name="backtest_result")
    op.drop_index("ix_backtest_result_stock_code_horizon_days", table_name="backtest_result")
    op.drop_table("backtest_result")
