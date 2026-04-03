"""Add news sentiment and event result tables.

Revision ID: 0003_news_sentiment_v1
Revises: 0002_news_module_v1
Create Date: 2026-04-02 12:05:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_news_sentiment_v1"
down_revision = "0002_news_module_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "news_sentiment_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("news_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=True),
        sa.Column("sentiment_label", sa.String(length=16), nullable=True),
        sa.Column("sentiment_score_base", sa.Numeric(8, 4), nullable=True),
        sa.Column("sentiment_score_adjusted", sa.Numeric(8, 4), nullable=True),
        sa.Column("confidence_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("heat_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("market_context_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("position_context_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("event_conflict_flag", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("news_id", name="uq_news_sentiment_result_news_id"),
    )
    op.create_index("ix_news_sentiment_result_news_id", "news_sentiment_result", ["news_id"])
    op.create_index("ix_news_sentiment_result_stock_code", "news_sentiment_result", ["stock_code"])
    op.create_index("ix_news_sentiment_result_sentiment_label", "news_sentiment_result", ["sentiment_label"])

    op.create_table(
        "news_event_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("news_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=True),
        sa.Column("sentence_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sentence_text", sa.Text(), nullable=True),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("event_polarity", sa.String(length=16), nullable=True),
        sa.Column("event_strength", sa.Integer(), nullable=True),
        sa.Column("entity_main", sa.String(length=128), nullable=True),
        sa.Column("entity_secondary", sa.String(length=128), nullable=True),
        sa.Column("trigger_keywords", sa.JSON(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "news_id",
            "sentence_index",
            "event_type",
            name="uq_news_event_result_news_id_sentence_index_event_type",
        ),
    )
    op.create_index("ix_news_event_result_news_id", "news_event_result", ["news_id"])
    op.create_index("ix_news_event_result_stock_code", "news_event_result", ["stock_code"])
    op.create_index("ix_news_event_result_event_type", "news_event_result", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_news_event_result_event_type", table_name="news_event_result")
    op.drop_index("ix_news_event_result_stock_code", table_name="news_event_result")
    op.drop_index("ix_news_event_result_news_id", table_name="news_event_result")
    op.drop_table("news_event_result")

    op.drop_index("ix_news_sentiment_result_sentiment_label", table_name="news_sentiment_result")
    op.drop_index("ix_news_sentiment_result_stock_code", table_name="news_sentiment_result")
    op.drop_index("ix_news_sentiment_result_news_id", table_name="news_sentiment_result")
    op.drop_table("news_sentiment_result")
