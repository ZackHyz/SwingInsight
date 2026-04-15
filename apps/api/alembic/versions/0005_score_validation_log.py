"""Add score validation log table.

Revision ID: 0005_score_validation_log
Revises: 0004_pattern_similarity_v1
Create Date: 2026-04-11 16:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_score_validation_log"
down_revision = "0004_pattern_similarity_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "score_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("query_window_id", sa.BigInteger(), nullable=True),
        sa.Column("query_end_date", sa.Date(), nullable=False),
        sa.Column("predicted_win_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("predicted_avg_return", sa.Numeric(10, 4), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("actual_return_5d", sa.Numeric(10, 4), nullable=True),
        sa.Column("actual_return_10d", sa.Numeric(10, 4), nullable=True),
        sa.Column("actual_outcome_5d", sa.Integer(), nullable=True),
        sa.Column("actual_outcome_10d", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_score_log_stock_code_query_end_date", "score_log", ["stock_code", "query_end_date"])
    op.create_index("ix_score_log_query_window_id", "score_log", ["query_window_id"])


def downgrade() -> None:
    op.drop_index("ix_score_log_query_window_id", table_name="score_log")
    op.drop_index("ix_score_log_stock_code_query_end_date", table_name="score_log")
    op.drop_table("score_log")
