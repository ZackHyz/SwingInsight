"""Add pattern similarity v1 tables.

Revision ID: 0004_pattern_similarity_v1
Revises: 0003_news_sentiment_v1
Create Date: 2026-04-02 15:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0004_pattern_similarity_v1"
down_revision = "0003_news_sentiment_v1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "pattern_window",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("window_uid", sa.String(length=128), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("segment_id", sa.BigInteger(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("window_size", sa.Integer(), nullable=False),
        sa.Column("start_close", sa.Numeric(12, 4), nullable=False),
        sa.Column("end_close", sa.Numeric(12, 4), nullable=False),
        sa.Column("period_pct_change", sa.Numeric(10, 4), nullable=True),
        sa.Column("highest_day_pos", sa.Integer(), nullable=True),
        sa.Column("lowest_day_pos", sa.Integer(), nullable=True),
        sa.Column("trend_label", sa.String(length=32), nullable=True),
        sa.Column("feature_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("window_uid", name="uq_pattern_window_window_uid"),
    )
    op.create_index(
        "ix_pattern_window_stock_code_start_date_end_date",
        "pattern_window",
        ["stock_code", "start_date", "end_date"],
    )
    op.create_index("ix_pattern_window_segment_id", "pattern_window", ["segment_id"])
    op.create_index("ix_pattern_window_stock_code_window_size", "pattern_window", ["stock_code", "window_size"])
    op.create_index("ix_pattern_window_feature_version", "pattern_window", ["feature_version"])

    op.create_table(
        "pattern_feature",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("window_id", sa.BigInteger(), nullable=False),
        sa.Column("price_seq_json", sa.JSON(), nullable=True),
        sa.Column("return_seq_json", sa.JSON(), nullable=True),
        sa.Column("candle_feat_json", sa.JSON(), nullable=True),
        sa.Column("volume_seq_json", sa.JSON(), nullable=True),
        sa.Column("turnover_seq_json", sa.JSON(), nullable=True),
        sa.Column("trend_context_json", sa.JSON(), nullable=True),
        sa.Column("vola_context_json", sa.JSON(), nullable=True),
        sa.Column("coarse_vector_json", sa.JSON(), nullable=True),
        sa.Column("feature_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("window_id", name="uq_pattern_feature_window_id"),
    )
    op.create_index("ix_pattern_feature_window_id", "pattern_feature", ["window_id"])
    op.create_index("ix_pattern_feature_feature_version", "pattern_feature", ["feature_version"])

    op.create_table(
        "pattern_future_stat",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("window_id", sa.BigInteger(), nullable=False),
        sa.Column("ret_1d", sa.Numeric(10, 4), nullable=True),
        sa.Column("ret_3d", sa.Numeric(10, 4), nullable=True),
        sa.Column("ret_5d", sa.Numeric(10, 4), nullable=True),
        sa.Column("ret_10d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_up_3d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_dd_3d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_up_5d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_dd_5d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_up_10d", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_dd_10d", sa.Numeric(10, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("window_id", name="uq_pattern_future_stat_window_id"),
    )
    op.create_index("ix_pattern_future_stat_window_id", "pattern_future_stat", ["window_id"])

    op.create_table(
        "pattern_match_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("query_signature", sa.String(length=128), nullable=False),
        sa.Column("query_window_id", sa.BigInteger(), nullable=True),
        sa.Column("target_window_id", sa.BigInteger(), nullable=False),
        sa.Column("rank_no", sa.Integer(), nullable=False),
        sa.Column("total_similarity", sa.Numeric(8, 4), nullable=True),
        sa.Column("sim_price", sa.Numeric(8, 4), nullable=True),
        sa.Column("sim_candle", sa.Numeric(8, 4), nullable=True),
        sa.Column("sim_volume", sa.Numeric(8, 4), nullable=True),
        sa.Column("sim_turnover", sa.Numeric(8, 4), nullable=True),
        sa.Column("sim_trend", sa.Numeric(8, 4), nullable=True),
        sa.Column("sim_vola", sa.Numeric(8, 4), nullable=True),
        sa.Column("feature_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "query_signature",
            "target_window_id",
            name="uq_pattern_match_result_query_signature_target_window_id",
        ),
    )
    op.create_index(
        "ix_pattern_match_result_query_signature_rank_no",
        "pattern_match_result",
        ["query_signature", "rank_no"],
    )
    op.create_index("ix_pattern_match_result_query_window_id", "pattern_match_result", ["query_window_id"])
    op.create_index("ix_pattern_match_result_target_window_id", "pattern_match_result", ["target_window_id"])
    op.create_index("ix_pattern_match_result_feature_version", "pattern_match_result", ["feature_version"])


def downgrade() -> None:
    op.drop_index("ix_pattern_match_result_feature_version", table_name="pattern_match_result")
    op.drop_index("ix_pattern_match_result_target_window_id", table_name="pattern_match_result")
    op.drop_index("ix_pattern_match_result_query_window_id", table_name="pattern_match_result")
    op.drop_index("ix_pattern_match_result_query_signature_rank_no", table_name="pattern_match_result")
    op.drop_table("pattern_match_result")

    op.drop_index("ix_pattern_future_stat_window_id", table_name="pattern_future_stat")
    op.drop_table("pattern_future_stat")

    op.drop_index("ix_pattern_feature_feature_version", table_name="pattern_feature")
    op.drop_index("ix_pattern_feature_window_id", table_name="pattern_feature")
    op.drop_table("pattern_feature")

    op.drop_index("ix_pattern_window_feature_version", table_name="pattern_window")
    op.drop_index("ix_pattern_window_stock_code_window_size", table_name="pattern_window")
    op.drop_index("ix_pattern_window_segment_id", table_name="pattern_window")
    op.drop_index("ix_pattern_window_stock_code_start_date_end_date", table_name="pattern_window")
    op.drop_table("pattern_window")
