"""Initial schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-03-30 16:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stock_basic",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("stock_name", sa.String(length=128), nullable=False),
        sa.Column("market", sa.String(length=16), nullable=False),
        sa.Column("industry", sa.String(length=128), nullable=True),
        sa.Column("concept_tags", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stock_code", name="uq_stock_basic_stock_code"),
    )
    op.create_index("ix_stock_basic_stock_code", "stock_basic", ["stock_code"])

    op.create_table(
        "daily_price",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("open_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("high_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("low_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("close_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("pre_close_price", sa.Numeric(12, 4), nullable=True),
        sa.Column("change_amount", sa.Numeric(12, 4), nullable=True),
        sa.Column("change_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("amplitude_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("turnover_rate", sa.Numeric(10, 4), nullable=True),
        sa.Column("adj_type", sa.String(length=16), nullable=False),
        sa.Column("adj_factor", sa.Numeric(20, 8), nullable=True),
        sa.Column("is_trading_day", sa.Boolean(), nullable=False),
        sa.Column("data_source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "stock_code",
            "trade_date",
            "adj_type",
            name="uq_daily_price_stock_code_trade_date_adj_type",
        ),
    )
    op.create_index("ix_daily_price_stock_code_trade_date", "daily_price", ["stock_code", "trade_date"])
    op.create_index("ix_daily_price_trade_date", "daily_price", ["trade_date"])

    op.create_table(
        "trade_record",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("trade_date", sa.Date(), nullable=False),
        sa.Column("trade_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trade_type", sa.String(length=16), nullable=False),
        sa.Column("price", sa.Numeric(12, 4), nullable=False),
        sa.Column("quantity", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(20, 2), nullable=True),
        sa.Column("fee", sa.Numeric(12, 2), nullable=True),
        sa.Column("tax", sa.Numeric(12, 2), nullable=True),
        sa.Column("account_id", sa.String(length=64), nullable=True),
        sa.Column("strategy_tag", sa.String(length=64), nullable=True),
        sa.Column("order_group_id", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_trade_record_stock_date", "trade_record", ["stock_code", "trade_date"])
    op.create_index("ix_trade_record_group_id", "trade_record", ["order_group_id"])
    op.create_index("ix_trade_record_strategy_tag", "trade_record", ["strategy_tag"])

    op.create_table(
        "algo_version",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("version_code", sa.String(length=64), nullable=False),
        sa.Column("algo_type", sa.String(length=32), nullable=False),
        sa.Column("version_name", sa.String(length=128), nullable=True),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("version_code", name="uq_algo_version_version_code"),
    )
    op.create_index("ix_algo_version_algo_type", "algo_version", ["algo_type"])

    op.create_table(
        "news_raw",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("news_uid", sa.String(length=128), nullable=True),
        sa.Column("stock_code", sa.String(length=16), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("publish_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("news_date", sa.Date(), nullable=True),
        sa.Column("source_name", sa.String(length=128), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("related_industry", sa.String(length=128), nullable=True),
        sa.Column("related_concept", sa.String(length=128), nullable=True),
        sa.Column("sentiment", sa.String(length=16), nullable=True),
        sa.Column("news_type", sa.String(length=32), nullable=True),
        sa.Column("keywords", sa.Text(), nullable=True),
        sa.Column("is_duplicate", sa.Boolean(), nullable=False),
        sa.Column("duplicate_group_id", sa.String(length=64), nullable=True),
        sa.Column("data_source", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_news_raw_stock_code", "news_raw", ["stock_code"])
    op.create_index("ix_news_raw_publish_time", "news_raw", ["publish_time"])
    op.create_index("ix_news_raw_news_date", "news_raw", ["news_date"])
    op.create_index("ix_news_raw_news_type", "news_raw", ["news_type"])
    op.create_index("ix_news_raw_duplicate_group", "news_raw", ["duplicate_group_id"])

    op.create_table(
        "turning_point",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("point_date", sa.Date(), nullable=False),
        sa.Column("point_type", sa.String(length=16), nullable=False),
        sa.Column("point_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("confirm_date", sa.Date(), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("version_code", sa.String(length=64), nullable=True),
        sa.Column("parent_point_id", sa.BigInteger(), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("confidence_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_turning_point_stock_date", "turning_point", ["stock_code", "point_date"])
    op.create_index("ix_turning_point_stock_type", "turning_point", ["stock_code", "point_type"])
    op.create_index("ix_turning_point_final", "turning_point", ["stock_code", "is_final"])
    op.create_index("ix_turning_point_version", "turning_point", ["version_code"])

    op.create_table(
        "point_revision_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("point_id", sa.BigInteger(), nullable=True),
        sa.Column("operation_type", sa.String(length=32), nullable=False),
        sa.Column("old_value_json", sa.JSON(), nullable=True),
        sa.Column("new_value_json", sa.JSON(), nullable=True),
        sa.Column("operator", sa.String(length=64), nullable=True),
        sa.Column("remark", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_point_revision_log_stock_code", "point_revision_log", ["stock_code"])
    op.create_index("ix_point_revision_log_point_id", "point_revision_log", ["point_id"])
    op.create_index("ix_point_revision_log_created_at", "point_revision_log", ["created_at"])

    op.create_table(
        "swing_segment",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("segment_uid", sa.String(length=64), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("start_point_id", sa.BigInteger(), nullable=True),
        sa.Column("end_point_id", sa.BigInteger(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("start_point_type", sa.String(length=16), nullable=False),
        sa.Column("end_point_type", sa.String(length=16), nullable=False),
        sa.Column("start_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("end_price", sa.Numeric(12, 4), nullable=False),
        sa.Column("pct_change", sa.Numeric(10, 4), nullable=True),
        sa.Column("duration_days", sa.Integer(), nullable=True),
        sa.Column("max_drawdown_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_rebound_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("max_upside_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("avg_daily_change_pct", sa.Numeric(10, 4), nullable=True),
        sa.Column("segment_type", sa.String(length=32), nullable=True),
        sa.Column("trend_direction", sa.String(length=16), nullable=True),
        sa.Column("source_version", sa.String(length=64), nullable=True),
        sa.Column("is_final", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("segment_uid", name="uq_swing_segment_segment_uid"),
    )
    op.create_index("ix_swing_segment_stock_date", "swing_segment", ["stock_code", "start_date", "end_date"])
    op.create_index("ix_swing_segment_stock_type", "swing_segment", ["stock_code", "segment_type"])
    op.create_index("ix_swing_segment_final", "swing_segment", ["stock_code", "is_final"])

    op.create_table(
        "segment_news_map",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("segment_id", sa.BigInteger(), nullable=False),
        sa.Column("news_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("relation_type", sa.String(length=32), nullable=False),
        sa.Column("window_type", sa.String(length=32), nullable=True),
        sa.Column("anchor_date", sa.Date(), nullable=True),
        sa.Column("distance_days", sa.Integer(), nullable=True),
        sa.Column("weight_score", sa.Numeric(8, 4), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "segment_id",
            "news_id",
            "relation_type",
            name="uq_segment_news_map_segment_id_news_id_relation_type",
        ),
    )
    op.create_index("ix_segment_news_map_segment_id", "segment_news_map", ["segment_id"])
    op.create_index("ix_segment_news_map_news_id", "segment_news_map", ["news_id"])
    op.create_index("ix_segment_news_map_stock_code", "segment_news_map", ["stock_code"])
    op.create_index("ix_segment_news_map_relation_type", "segment_news_map", ["relation_type"])

    op.create_table(
        "segment_feature",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("segment_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("feature_group", sa.String(length=32), nullable=False),
        sa.Column("feature_name", sa.String(length=128), nullable=False),
        sa.Column("feature_value_num", sa.Numeric(20, 6), nullable=True),
        sa.Column("feature_value_text", sa.String(length=512), nullable=True),
        sa.Column("feature_value_json", sa.JSON(), nullable=True),
        sa.Column("version_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "segment_id",
            "feature_name",
            "version_code",
            name="uq_segment_feature_segment_id_feature_name_version_code",
        ),
    )
    op.create_index("ix_segment_feature_segment_id", "segment_feature", ["segment_id"])
    op.create_index("ix_segment_feature_stock_code", "segment_feature", ["stock_code"])
    op.create_index("ix_segment_feature_group_name", "segment_feature", ["feature_group", "feature_name"])
    op.create_index("ix_segment_feature_version", "segment_feature", ["version_code"])

    op.create_table(
        "segment_label",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("segment_id", sa.BigInteger(), nullable=False),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("label_type", sa.String(length=32), nullable=False),
        sa.Column("label_name", sa.String(length=128), nullable=False),
        sa.Column("label_value", sa.String(length=128), nullable=True),
        sa.Column("score", sa.Numeric(8, 4), nullable=True),
        sa.Column("source_type", sa.String(length=16), nullable=False),
        sa.Column("version_code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_segment_label_segment_id", "segment_label", ["segment_id"])
    op.create_index("ix_segment_label_stock_code", "segment_label", ["stock_code"])
    op.create_index("ix_segment_label_type_name", "segment_label", ["label_type", "label_name"])

    op.create_table(
        "prediction_result",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("stock_code", sa.String(length=16), nullable=False),
        sa.Column("predict_date", sa.Date(), nullable=False),
        sa.Column("current_state", sa.String(length=64), nullable=False),
        sa.Column("up_prob_5d", sa.Numeric(8, 4), nullable=True),
        sa.Column("flat_prob_5d", sa.Numeric(8, 4), nullable=True),
        sa.Column("down_prob_5d", sa.Numeric(8, 4), nullable=True),
        sa.Column("up_prob_10d", sa.Numeric(8, 4), nullable=True),
        sa.Column("flat_prob_10d", sa.Numeric(8, 4), nullable=True),
        sa.Column("down_prob_10d", sa.Numeric(8, 4), nullable=True),
        sa.Column("up_prob_20d", sa.Numeric(8, 4), nullable=True),
        sa.Column("flat_prob_20d", sa.Numeric(8, 4), nullable=True),
        sa.Column("down_prob_20d", sa.Numeric(8, 4), nullable=True),
        sa.Column("similarity_topn_json", sa.JSON(), nullable=True),
        sa.Column("key_features_json", sa.JSON(), nullable=True),
        sa.Column("risk_flags_json", sa.JSON(), nullable=True),
        sa.Column("model_version", sa.String(length=64), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "stock_code",
            "predict_date",
            "model_version",
            name="uq_prediction_result_stock_code_predict_date_model_version",
        ),
    )
    op.create_index("ix_prediction_result_stock_date", "prediction_result", ["stock_code", "predict_date"])
    op.create_index("ix_prediction_result_state", "prediction_result", ["current_state"])
    op.create_index("ix_prediction_result_model_version", "prediction_result", ["model_version"])

    op.create_table(
        "task_run_log",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("task_name", sa.String(length=128), nullable=False),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("target_code", sa.String(length=32), nullable=True),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.BigInteger(), nullable=True),
        sa.Column("input_params_json", sa.JSON(), nullable=True),
        sa.Column("result_summary", sa.Text(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_task_run_log_task_name", "task_run_log", ["task_name"])
    op.create_index("ix_task_run_log_target_code", "task_run_log", ["target_code"])
    op.create_index("ix_task_run_log_status", "task_run_log", ["status"])
    op.create_index("ix_task_run_log_start_time", "task_run_log", ["start_time"])


def downgrade() -> None:
    for index_name, table_name in [
        ("ix_task_run_log_start_time", "task_run_log"),
        ("ix_task_run_log_status", "task_run_log"),
        ("ix_task_run_log_target_code", "task_run_log"),
        ("ix_task_run_log_task_name", "task_run_log"),
        ("ix_prediction_result_model_version", "prediction_result"),
        ("ix_prediction_result_state", "prediction_result"),
        ("ix_prediction_result_stock_date", "prediction_result"),
        ("ix_segment_label_type_name", "segment_label"),
        ("ix_segment_label_stock_code", "segment_label"),
        ("ix_segment_label_segment_id", "segment_label"),
        ("ix_segment_feature_version", "segment_feature"),
        ("ix_segment_feature_group_name", "segment_feature"),
        ("ix_segment_feature_stock_code", "segment_feature"),
        ("ix_segment_feature_segment_id", "segment_feature"),
        ("ix_segment_news_map_relation_type", "segment_news_map"),
        ("ix_segment_news_map_stock_code", "segment_news_map"),
        ("ix_segment_news_map_news_id", "segment_news_map"),
        ("ix_segment_news_map_segment_id", "segment_news_map"),
        ("ix_swing_segment_final", "swing_segment"),
        ("ix_swing_segment_stock_type", "swing_segment"),
        ("ix_swing_segment_stock_date", "swing_segment"),
        ("ix_point_revision_log_created_at", "point_revision_log"),
        ("ix_point_revision_log_point_id", "point_revision_log"),
        ("ix_point_revision_log_stock_code", "point_revision_log"),
        ("ix_turning_point_version", "turning_point"),
        ("ix_turning_point_final", "turning_point"),
        ("ix_turning_point_stock_type", "turning_point"),
        ("ix_turning_point_stock_date", "turning_point"),
        ("ix_news_raw_duplicate_group", "news_raw"),
        ("ix_news_raw_news_type", "news_raw"),
        ("ix_news_raw_news_date", "news_raw"),
        ("ix_news_raw_publish_time", "news_raw"),
        ("ix_news_raw_stock_code", "news_raw"),
        ("ix_algo_version_algo_type", "algo_version"),
        ("ix_trade_record_strategy_tag", "trade_record"),
        ("ix_trade_record_group_id", "trade_record"),
        ("ix_trade_record_stock_date", "trade_record"),
        ("ix_daily_price_trade_date", "daily_price"),
        ("ix_daily_price_stock_code_trade_date", "daily_price"),
        ("ix_stock_basic_stock_code", "stock_basic"),
    ]:
        op.drop_index(index_name, table_name=table_name)

    for table_name in [
        "task_run_log",
        "prediction_result",
        "segment_label",
        "segment_feature",
        "segment_news_map",
        "swing_segment",
        "point_revision_log",
        "turning_point",
        "news_raw",
        "algo_version",
        "trade_record",
        "daily_price",
        "stock_basic",
    ]:
        op.drop_table(table_name)
