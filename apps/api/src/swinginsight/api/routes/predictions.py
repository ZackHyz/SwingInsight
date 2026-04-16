from __future__ import annotations

from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SwingSegment
from swinginsight.services.current_news_window_service import build_current_news_summary
from swinginsight.services.prediction_service import PredictionService, SimilarCase, SIMILAR_CASE_RETURN_HORIZONS


def _serialize_similar_case(case: SimilarCase) -> dict[str, object]:
    return {
        "segment_id": case.segment_id,
        "stock_code": case.stock_code,
        "score": case.score,
        "price_score": case.price_score,
        "volume_score": case.volume_score,
        "turnover_score": case.turnover_score,
        "pattern_score": case.pattern_score,
        "candle_score": case.candle_score,
        "trend_score": case.trend_score,
        "vola_score": case.vola_score,
        "window_id": case.window_id,
        "window_start_date": case.window_start_date.isoformat() if case.window_start_date else None,
        "window_end_date": case.window_end_date.isoformat() if case.window_end_date else None,
        "window_size": case.window_size,
        "segment_start_date": case.segment_start_date.isoformat() if case.segment_start_date else None,
        "segment_end_date": case.segment_end_date.isoformat() if case.segment_end_date else None,
        "pct_change": case.pct_change,
        "start_date": case.start_date.isoformat(),
        "end_date": case.end_date.isoformat(),
        **{f"return_{horizon}d": case.forward_returns.get(horizon) for horizon in SIMILAR_CASE_RETURN_HORIZONS},
    }


def get_prediction_payload(session: Session, stock_code: str, predict_date: date) -> dict[str, object]:
    result = PredictionService(session).predict(stock_code, predict_date)
    return {
        "stock_code": stock_code,
        "predict_date": predict_date.isoformat(),
        "current_state": result.current_state,
        "summary": result.summary,
        "fallback_used": result.fallback_used,
        "fallback_reason": result.fallback_reason,
        "fallback_error_type": result.fallback_error_type,
        "fallback_stage": result.fallback_stage,
        "probabilities": {
            "up_1d": result.up_prob_1d,
            "flat_1d": result.flat_prob_1d,
            "down_1d": result.down_prob_1d,
            "up_5d": result.up_prob_5d,
            "flat_5d": result.flat_prob_5d,
            "down_5d": result.down_prob_5d,
            "up_10d": result.up_prob_10d,
            "flat_10d": result.flat_prob_10d,
            "down_10d": result.down_prob_10d,
            "up_20d": result.up_prob_20d,
            "flat_20d": result.flat_prob_20d,
            "down_20d": result.down_prob_20d,
        },
        "key_features": result.key_features,
        "risk_flags": result.risk_flags,
        "news_summary": build_current_news_summary(session, stock_code, predict_date),
        "group_stat": result.group_stat,
        "query_window": _serialize_query_window(result.query_window),
        "similar_cases": [_serialize_similar_case(case) for case in result.similar_cases],
    }


def load_latest_prediction_summary(session: Session, stock_code: str) -> dict[str, object] | None:
    latest_trade_date = session.scalar(select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_code == stock_code))
    if latest_trade_date is None:
        return None
    try:
        result = PredictionService(session).predict(stock_code, latest_trade_date)
    except ValueError:
        return None
    return {
        "label": result.current_state,
        "summary": result.summary or "预测结果待生成",
        "probabilities": {
            "up_1d": result.up_prob_1d,
            "flat_1d": result.flat_prob_1d,
            "down_1d": result.down_prob_1d,
            "up_5d": result.up_prob_5d,
            "flat_5d": result.flat_prob_5d,
            "down_5d": result.down_prob_5d,
            "up_10d": result.up_prob_10d,
            "flat_10d": result.flat_prob_10d,
            "down_10d": result.down_prob_10d,
            "up_20d": result.up_prob_20d,
            "flat_20d": result.flat_prob_20d,
            "down_20d": result.down_prob_20d,
        },
        "key_features": result.key_features,
        "risk_flags": result.risk_flags,
        "news_summary": build_current_news_summary(session, stock_code, latest_trade_date),
        "group_stat": result.group_stat,
        "query_window": _serialize_query_window(result.query_window),
        "similar_cases": [_serialize_similar_case(case) for case in result.similar_cases],
    }


def _enrich_similar_cases(session: Session, items: list[dict[str, object]]) -> list[dict[str, object]]:
    enriched: list[dict[str, object]] = []
    for item in items:
        payload = dict(item)
        needs_dates = payload.get("start_date") in (None, "") or payload.get("end_date") in (None, "")
        if needs_dates and isinstance(payload.get("segment_id"), int):
            segment = session.scalar(select(SwingSegment).where(SwingSegment.id == payload["segment_id"]))
            if segment is not None:
                payload["start_date"] = segment.start_date.isoformat()
                payload["end_date"] = segment.end_date.isoformat()
        enriched.append(payload)
    return enriched


def _serialize_query_window(query_window: dict[str, object] | None) -> dict[str, object] | None:
    if query_window is None:
        return None
    start_date = query_window.get("start_date")
    end_date = query_window.get("end_date")
    return {
        "window_id": query_window.get("window_id"),
        "segment_id": query_window.get("segment_id"),
        "start_date": start_date.isoformat() if isinstance(start_date, date) else start_date,
        "end_date": end_date.isoformat() if isinstance(end_date, date) else end_date,
        "window_size": query_window.get("window_size"),
    }
