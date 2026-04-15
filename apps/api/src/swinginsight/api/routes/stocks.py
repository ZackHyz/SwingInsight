from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice, TradeRecord
from swinginsight.db.models.news import (
    NewsEventResult,
    NewsProcessed,
    NewsRaw,
    NewsSentimentResult,
    PointNewsMap,
    SegmentNewsMap,
)
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.api.routes.predictions import load_latest_prediction_summary
from swinginsight.services.news_sentiment_service import (
    adjust_sentiment_with_position,
    resolve_base_sentiment_score,
    resolve_heat_score,
)
from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService


def get_stock_research_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == stock_code))
    if stock is None:
        return None

    prices = session.scalars(
        select(DailyPrice).where(DailyPrice.stock_code == stock_code).order_by(DailyPrice.trade_date.asc())
    ).all()
    auto_points = session.scalars(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.source_type == "system")
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    final_points = session.scalars(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    current_segment = session.scalar(
        select(SwingSegment)
        .where(SwingSegment.stock_code == stock_code, SwingSegment.is_final.is_(True))
        .order_by(SwingSegment.end_date.desc(), SwingSegment.id.desc())
        .limit(1)
    )
    current_point = final_points[-1] if final_points else None
    trade_markers = session.scalars(
        select(TradeRecord).where(TradeRecord.stock_code == stock_code).order_by(TradeRecord.trade_date.asc(), TradeRecord.id.asc())
    ).all()
    news_rows = session.execute(
        select(NewsRaw, NewsProcessed, NewsSentimentResult)
        .outerjoin(NewsProcessed, NewsProcessed.news_id == NewsRaw.id)
        .outerjoin(NewsSentimentResult, NewsSentimentResult.news_id == NewsRaw.id)
        .where(NewsRaw.stock_code == stock_code)
        .order_by(NewsRaw.news_date.desc(), NewsRaw.id.desc())
        .limit(12)
    ).all()
    news_ids = [raw.id for raw, _, _ in news_rows]
    current_segment_mappings = _load_segment_news_mappings(session, current_segment=current_segment, news_ids=news_ids)
    current_point_mappings = _load_point_news_mappings(session, current_point=current_point, news_ids=news_ids)
    event_metadata_by_news = _load_event_metadata(session, news_ids=news_ids)
    prediction = load_latest_prediction_summary(session, stock_code)

    news_items: list[dict[str, object]] = []
    news_summary_items: list[dict[str, object]] = []
    for raw, processed, sentiment_result in news_rows:
        category = _resolve_news_category(raw=raw, processed=processed)
        sentiment = _resolve_news_sentiment(raw=raw, processed=processed, sentiment_result=sentiment_result)
        segment_mapping = current_segment_mappings.get(raw.id)
        point_mapping = current_point_mappings.get(raw.id)
        relation_type = _resolve_relation_type(segment_mapping=segment_mapping, point_mapping=point_mapping)
        event_metadata = event_metadata_by_news.get(raw.id, {"event_types": [], "positive_event_count": 0, "negative_event_count": 0})
        adjusted_sentiment = adjust_sentiment_with_position(
            base_score=resolve_base_sentiment_score(
                sentiment_result.sentiment_score_base if sentiment_result is not None else None,
                sentiment,
            ),
            category=category,
            relation_type=relation_type,
            point_type=point_mapping.point_type if point_mapping is not None else None,
            heat_score=resolve_heat_score(
                sentiment_result.heat_score if sentiment_result is not None else None,
                processed.heat_level if processed is not None else None,
            ),
            event_types=event_metadata["event_types"],
        )
        news_items.append(
            {
                "news_id": raw.id,
                "title": raw.title,
                "summary": raw.summary,
                "source_name": raw.source_name,
                "source_type": raw.source_type,
                "news_date": raw.news_date.isoformat() if raw.news_date else None,
                "category": category,
                "sub_category": processed.sub_category if processed is not None else None,
                "sentiment": sentiment,
                "display_tags": _build_display_tags(
                    category=category,
                    sentiment=sentiment,
                    segment_mapping=segment_mapping,
                    point_mapping=point_mapping,
                ),
                "sentiment_score_adjusted": adjusted_sentiment,
                "event_types": event_metadata["event_types"],
                "event_conflict_flag": bool(sentiment_result.event_conflict_flag) if sentiment_result is not None else False,
            }
        )
        news_summary_items.append(
            {
                "category": category,
                "sentiment": sentiment,
                "heat_level": processed.heat_level if processed is not None else None,
                "sentiment_score_adjusted": adjusted_sentiment,
                "positive_event_count": event_metadata["positive_event_count"],
                "negative_event_count": event_metadata["negative_event_count"],
                "governance_event_count": 1 if "governance" in event_metadata["event_types"] else 0,
            }
        )

    current_state = (
        dict(prediction)
        if prediction
        else {
            "label": "待生成",
            "summary": "预测结果待生成",
            "probabilities": {},
            "key_features": {},
            "risk_flags": {},
            "similar_cases": [],
        }
    )
    current_state["news_summary"] = _build_research_news_summary(news_summary_items)

    return {
        "stock": {
            "stock_code": stock.stock_code,
            "stock_name": stock.stock_name,
            "market": stock.market,
            "industry": stock.industry,
            "concept_tags": stock.concept_tags or [],
        },
        "prices": [
            {
                "trade_date": row.trade_date.isoformat(),
                "open_price": float(row.open_price),
                "high_price": float(row.high_price),
                "low_price": float(row.low_price),
                "close_price": float(row.close_price),
                "volume": int(row.volume) if row.volume is not None else None,
            }
            for row in prices
        ],
        "auto_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in auto_points
        ],
        "final_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in final_points
        ],
        "trade_markers": [
            {
                "id": row.id,
                "trade_date": row.trade_date.isoformat(),
                "trade_type": row.trade_type,
                "price": float(row.price),
                "quantity": row.quantity,
                "strategy_tag": row.strategy_tag,
                "note": row.note,
            }
            for row in trade_markers
        ],
        "news_items": news_items,
        "current_state": current_state,
    }


def get_pattern_score_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    snapshot = get_pattern_score_snapshot(session, stock_code)
    if snapshot is None:
        return None
    return snapshot["payload"]


def get_pattern_score_snapshot(session: Session, stock_code: str) -> dict[str, object] | None:
    summary = load_latest_prediction_summary(session, stock_code)
    if summary is None:
        return None
    similar_cases = _resolve_similar_cases(summary)
    horizon = 10
    raw_win_rate_5d = _win_rate(similar_cases, horizon=5)
    raw_win_rate_10d = _win_rate(similar_cases, horizon=10)
    calibration_service = PatternScoreCalibrationService(session)
    win_rate_5d, calibrated_5d = calibration_service.predict_with_meta(
        stock_code=stock_code,
        raw_score=raw_win_rate_5d,
        horizon_days=5,
        method="platt",
    )
    win_rate_10d, calibrated_10d = calibration_service.predict_with_meta(
        stock_code=stock_code,
        raw_score=raw_win_rate_10d,
        horizon_days=10,
        method="platt",
    )
    weighted = _weighted_return(similar_cases, horizon=horizon)
    sample_count = int(weighted["sample_count"])
    payload = {
        "horizon_days": horizon,
        "raw_win_rate": raw_win_rate_10d,
        "win_rate_5d": round(win_rate_5d, 4),
        "win_rate_10d": round(win_rate_10d, 4),
        "win_rate": round(win_rate_10d, 4),
        "avg_return": weighted["avg_return"],
        "sample_count": sample_count,
        "confidence": _resolve_confidence(sample_count),
        "calibrated": bool(calibrated_5d and calibrated_10d),
    }
    query_window = summary.get("query_window") if isinstance(summary, dict) else None
    query_window_id = query_window.get("window_id") if isinstance(query_window, dict) else None
    end_value = query_window.get("end_date") if isinstance(query_window, dict) else None
    query_end_date = _as_iso_date(end_value)
    if query_end_date is None:
        query_end_date = session.scalar(select(DailyPrice.trade_date).where(DailyPrice.stock_code == stock_code).order_by(DailyPrice.trade_date.desc(), DailyPrice.id.desc()))
    return {
        "payload": payload,
        "query_window_id": query_window_id if isinstance(query_window_id, int) else None,
        "query_end_date": query_end_date,
    }


def get_pattern_similar_cases_payload(session: Session, stock_code: str, *, top_k: int = 10) -> list[dict[str, object]] | None:
    summary = load_latest_prediction_summary(session, stock_code)
    if summary is None:
        return None
    items = _resolve_similar_cases(summary)[:max(top_k, 0)]
    return [
        {
            "window_id": item.get("window_id"),
            "window_start_date": item.get("window_start_date"),
            "window_end_date": item.get("window_end_date"),
            "segment_start_date": item.get("segment_start_date") or item.get("start_date"),
            "segment_end_date": item.get("segment_end_date") or item.get("end_date"),
            "similarity_score": float(item.get("score") or 0.0),
            "future_return_5d": item.get("return_5d"),
            "future_return_10d": item.get("return_10d"),
            "future_return_20d": item.get("return_20d"),
            "stock_code": item.get("stock_code"),
            "segment_id": item.get("segment_id"),
        }
        for item in items
    ]


def get_pattern_group_stat_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    summary = load_latest_prediction_summary(session, stock_code)
    if summary is None:
        return None
    similar_cases = _resolve_similar_cases(summary)
    horizons = (5, 10, 20)
    return_distributions = {
        str(horizon): _return_distribution(similar_cases, horizon=horizon) for horizon in horizons
    }
    return {
        "horizon_days": list(horizons),
        "win_rates": [_win_rate(similar_cases, horizon=horizon) for horizon in horizons],
        "avg_returns": [_weighted_return(similar_cases, horizon=horizon)["avg_return"] for horizon in horizons],
        "sample_counts": [_sample_count(similar_cases, horizon=horizon) for horizon in horizons],
        "return_distribution": return_distributions["10"],
        "return_distributions": return_distributions,
    }


def _load_segment_news_mappings(
    session: Session,
    *,
    current_segment: SwingSegment | None,
    news_ids: list[int],
) -> dict[int, SegmentNewsMap]:
    if current_segment is None or not news_ids:
        return {}
    mappings = session.scalars(
        select(SegmentNewsMap).where(
            SegmentNewsMap.segment_id == current_segment.id,
            SegmentNewsMap.news_id.in_(news_ids),
        )
    ).all()
    return {mapping.news_id: mapping for mapping in mappings}


def _load_point_news_mappings(
    session: Session,
    *,
    current_point: TurningPoint | None,
    news_ids: list[int],
) -> dict[int, PointNewsMap]:
    if current_point is None or not news_ids:
        return {}
    mappings = session.scalars(
        select(PointNewsMap).where(
            PointNewsMap.point_id == current_point.id,
            PointNewsMap.news_id.in_(news_ids),
        )
    ).all()
    return {mapping.news_id: mapping for mapping in mappings}


def _resolve_news_category(*, raw: NewsRaw, processed: NewsProcessed | None) -> str | None:
    if processed is not None and processed.category is not None:
        return processed.category
    if raw.source_type in {"announcement", "media_news"}:
        return raw.source_type
    return None


def _load_event_metadata(session: Session, *, news_ids: list[int]) -> dict[int, dict[str, object]]:
    if not news_ids:
        return {}
    rows = session.execute(
        select(NewsEventResult.news_id, NewsEventResult.event_type, NewsEventResult.event_polarity)
        .where(NewsEventResult.news_id.in_(news_ids))
        .order_by(NewsEventResult.news_id.asc(), NewsEventResult.sentence_index.asc(), NewsEventResult.event_type.asc())
    ).all()
    event_metadata_by_news: dict[int, dict[str, object]] = {}
    for news_id, event_type, event_polarity in rows:
        metadata = event_metadata_by_news.setdefault(
            news_id,
            {"event_types": [], "positive_event_count": 0, "negative_event_count": 0},
        )
        event_types = metadata["event_types"]
        if event_type not in event_types:
            event_types.append(event_type)
        if event_polarity == "positive":
            metadata["positive_event_count"] += 1
        elif event_polarity == "negative":
            metadata["negative_event_count"] += 1
    return event_metadata_by_news


def _resolve_news_sentiment(
    *,
    raw: NewsRaw,
    processed: NewsProcessed | None,
    sentiment_result: NewsSentimentResult | None = None,
) -> str | None:
    if sentiment_result is not None and sentiment_result.sentiment_label is not None:
        return sentiment_result.sentiment_label
    return processed.sentiment if processed is not None else raw.sentiment


def _resolve_relation_type(
    *,
    segment_mapping: SegmentNewsMap | None,
    point_mapping: PointNewsMap | None,
) -> str | None:
    if segment_mapping is not None and segment_mapping.relation_type != "inside_segment":
        return segment_mapping.relation_type
    if point_mapping is not None:
        return point_mapping.relation_type
    if segment_mapping is not None:
        return segment_mapping.relation_type
    return None


def _build_research_news_summary(items: list[dict[str, object]]) -> dict[str, float]:
    total = len(items)
    if total == 0:
        return {
            "window_news_count": 0.0,
            "announcement_count": 0.0,
            "positive_news_ratio": 0.0,
            "high_heat_count": 0.0,
            "avg_adjusted_sentiment": 0.0,
            "positive_event_count": 0.0,
            "negative_event_count": 0.0,
            "governance_event_count": 0.0,
        }

    announcement_count = sum(1 for item in items if item["category"] == "announcement")
    positive_news_count = sum(1 for item in items if item["sentiment"] == "positive")
    high_heat_count = sum(1 for item in items if item["heat_level"] == "high")
    positive_event_count = sum(int(item["positive_event_count"]) for item in items)
    negative_event_count = sum(int(item["negative_event_count"]) for item in items)
    governance_event_count = sum(int(item["governance_event_count"]) for item in items)
    adjusted_scores = [float(item["sentiment_score_adjusted"]) for item in items]

    return {
        "window_news_count": float(total),
        "announcement_count": float(announcement_count),
        "positive_news_ratio": positive_news_count / total,
        "high_heat_count": float(high_heat_count),
        "avg_adjusted_sentiment": round(sum(adjusted_scores) / len(adjusted_scores), 4) if adjusted_scores else 0.0,
        "positive_event_count": float(positive_event_count),
        "negative_event_count": float(negative_event_count),
        "governance_event_count": float(governance_event_count),
    }


def _build_display_tags(
    *,
    category: str | None,
    sentiment: str | None,
    segment_mapping: SegmentNewsMap | None,
    point_mapping: PointNewsMap | None,
) -> list[str]:
    tags: list[str] = []

    segment_tag = _segment_relation_tag(segment_mapping)
    if segment_tag is not None:
        tags.append(segment_tag)

    point_tag = _point_relation_tag(point_mapping)
    if point_tag is not None and point_tag not in tags:
        tags.append(point_tag)

    category_tag = _category_tag(category)
    if category_tag is not None and category_tag not in tags:
        tags.append(category_tag)

    sentiment_tag = _sentiment_tag(sentiment)
    if sentiment_tag is not None and sentiment_tag not in tags:
        tags.append(sentiment_tag)

    return tags


def _segment_relation_tag(mapping: SegmentNewsMap | None) -> str | None:
    if mapping is None:
        return None
    if mapping.relation_type == "inside_segment":
        return "当前波段内"
    if mapping.relation_type.startswith("before_"):
        if mapping.distance_days is None:
            return "波段起点前"
        return f"波段起点前{abs(mapping.distance_days)}日"
    if mapping.relation_type.startswith("after_"):
        if mapping.distance_days is None:
            return "波段终点后"
        return f"波段终点后{abs(mapping.distance_days)}日"
    return None


def _point_relation_tag(mapping: PointNewsMap | None) -> str | None:
    if mapping is None:
        return None
    point_label = "顶部" if mapping.point_type == "peak" else "底部"
    if mapping.distance_days is None or mapping.distance_days == 0:
        return f"{point_label}附近"
    if mapping.distance_days < 0:
        return f"{point_label}前{abs(mapping.distance_days)}日"
    return f"{point_label}后{mapping.distance_days}日"


def _category_tag(category: str | None) -> str | None:
    if category == "announcement":
        return "公告"
    if category == "media_news":
        return "资讯"
    return None


def _sentiment_tag(sentiment: str | None) -> str | None:
    if sentiment == "positive":
        return "利多"
    if sentiment == "negative":
        return "利空"
    if sentiment == "neutral":
        return "中性"
    return None


def _resolve_similar_cases(summary: dict[str, object]) -> list[dict[str, object]]:
    items = summary.get("similar_cases")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_iso_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _weighted_return(similar_cases: list[dict[str, object]], *, horizon: int) -> dict[str, float | int]:
    weighted_sum = 0.0
    weight_total = 0.0
    sample_count = 0
    for item in similar_cases:
        future_return = _safe_float(item.get(f"return_{horizon}d"))
        if future_return is None:
            continue
        weight = _safe_float(item.get("score")) or 0.0
        if weight <= 0:
            weight = 0.0001
        weighted_sum += weight * future_return
        weight_total += weight
        sample_count += 1
    if sample_count == 0:
        return {"avg_return": 0.0, "sample_count": 0}
    avg_return = weighted_sum / weight_total if weight_total > 0 else 0.0
    return {"avg_return": round(avg_return, 4), "sample_count": sample_count}


def _sample_count(similar_cases: list[dict[str, object]], *, horizon: int) -> int:
    return sum(1 for item in similar_cases if _safe_float(item.get(f"return_{horizon}d")) is not None)


def _win_rate(similar_cases: list[dict[str, object]], *, horizon: int) -> float:
    values = [
        value
        for value in (_safe_float(item.get(f"return_{horizon}d")) for item in similar_cases)
        if value is not None
    ]
    if not values:
        return 0.0
    return round(sum(1 for value in values if value > 0) / len(values), 4)


def _resolve_confidence(sample_count: int) -> str:
    if sample_count >= 30:
        return "high"
    if sample_count >= 10:
        return "medium"
    return "low"


def _return_distribution(similar_cases: list[dict[str, object]], *, horizon: int) -> list[float]:
    values = [
        value
        for value in (_safe_float(item.get(f"return_{horizon}d")) for item in similar_cases)
        if value is not None
    ]
    return sorted(round(value, 4) for value in values)
