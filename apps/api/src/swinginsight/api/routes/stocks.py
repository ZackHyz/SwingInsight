from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.api.assemblers.pattern_insight_assembler import (
    build_pattern_group_stat_payload,
    build_pattern_score_snapshot,
    build_pattern_similar_cases_payload,
    resolve_query_end_date,
)
from swinginsight.api.assemblers.stock_research_assembler import build_stock_research_payload
from swinginsight.api.readers.stock_research_reader import load_stock_research_snapshot
from swinginsight.api.routes.predictions import load_latest_prediction_summary
from swinginsight.db.models.market_data import DailyPrice
from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService


def get_stock_research_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    snapshot = load_stock_research_snapshot(session, stock_code)
    if snapshot is None:
        return None
    return build_stock_research_payload(snapshot)


def get_pattern_score_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    snapshot = get_pattern_score_snapshot(session, stock_code)
    if snapshot is None:
        return None
    return snapshot["payload"]


def get_pattern_score_snapshot(session: Session, stock_code: str) -> dict[str, object] | None:
    summary = load_latest_prediction_summary(session, stock_code)
    if summary is None:
        return None
    query_end_date = resolve_query_end_date(summary)
    if query_end_date is None:
        query_end_date = session.scalar(
            select(DailyPrice.trade_date)
            .where(DailyPrice.stock_code == stock_code)
            .order_by(DailyPrice.trade_date.desc(), DailyPrice.id.desc())
        )
    return build_pattern_score_snapshot(
        summary,
        stock_code=stock_code,
        calibration_service=PatternScoreCalibrationService(session),
        query_end_date=query_end_date,
    )


def get_pattern_similar_cases_payload(session: Session, stock_code: str, *, top_k: int = 10) -> list[dict[str, object]] | None:
    summary = load_latest_prediction_summary(session, stock_code)
    if summary is None:
        return None
    return build_pattern_similar_cases_payload(summary, top_k=top_k)


def get_pattern_group_stat_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    summary = load_latest_prediction_summary(session, stock_code)
    if summary is None:
        return None
    return build_pattern_group_stat_payload(summary)
