"""Add context feature json column to pattern_feature.

Revision ID: 0007_pattern_context_features
Revises: 0006_backtest_result
Create Date: 2026-04-11 18:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0007_pattern_context_features"
down_revision = "0006_backtest_result"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("pattern_feature", sa.Column("context_feature_json", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("pattern_feature", "context_feature_json")
