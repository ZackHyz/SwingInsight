from __future__ import annotations

from swinginsight.api.readers.stock_research_reader import StockResearchSnapshot
from swinginsight.db.models.news import NewsProcessed, NewsRaw, NewsSentimentResult, PointNewsMap, SegmentNewsMap
from swinginsight.services.news_sentiment_service import (
    adjust_sentiment_with_position,
    resolve_base_sentiment_score,
    resolve_heat_score,
)


def build_stock_research_payload(snapshot: StockResearchSnapshot) -> dict[str, object]:
    news_items: list[dict[str, object]] = []
    news_summary_items: list[dict[str, object]] = []
    for row in snapshot.news_rows:
        category = _resolve_news_category(raw=row.raw, processed=row.processed)
        sentiment = _resolve_news_sentiment(
            raw=row.raw,
            processed=row.processed,
            sentiment_result=row.sentiment_result,
        )
        relation_type = _resolve_relation_type(
            segment_mapping=row.segment_mapping,
            point_mapping=row.point_mapping,
        )
        event_metadata = row.event_metadata
        adjusted_sentiment = adjust_sentiment_with_position(
            base_score=resolve_base_sentiment_score(
                row.sentiment_result.sentiment_score_base if row.sentiment_result is not None else None,
                sentiment,
            ),
            category=category,
            relation_type=relation_type,
            point_type=row.point_mapping.point_type if row.point_mapping is not None else None,
            heat_score=resolve_heat_score(
                row.sentiment_result.heat_score if row.sentiment_result is not None else None,
                row.processed.heat_level if row.processed is not None else None,
            ),
            event_types=event_metadata["event_types"],
        )
        news_items.append(
            {
                "news_id": row.raw.id,
                "title": row.raw.title,
                "summary": row.raw.summary,
                "source_name": row.raw.source_name,
                "source_type": row.raw.source_type,
                "news_date": row.raw.news_date.isoformat() if row.raw.news_date else None,
                "category": category,
                "sub_category": row.processed.sub_category if row.processed is not None else None,
                "sentiment": sentiment,
                "display_tags": _build_display_tags(
                    category=category,
                    sentiment=sentiment,
                    segment_mapping=row.segment_mapping,
                    point_mapping=row.point_mapping,
                ),
                "sentiment_score_adjusted": adjusted_sentiment,
                "event_types": event_metadata["event_types"],
                "event_conflict_flag": bool(row.sentiment_result.event_conflict_flag)
                if row.sentiment_result is not None
                else False,
            }
        )
        news_summary_items.append(
            {
                "category": category,
                "sentiment": sentiment,
                "heat_level": row.processed.heat_level if row.processed is not None else None,
                "sentiment_score_adjusted": adjusted_sentiment,
                "positive_event_count": event_metadata["positive_event_count"],
                "negative_event_count": event_metadata["negative_event_count"],
                "governance_event_count": 1 if "governance" in event_metadata["event_types"] else 0,
            }
        )

    current_state = (
        dict(snapshot.prediction)
        if snapshot.prediction
        else {
            "label": "待生成",
            "summary": "预测结果待生成",
            "probabilities": {},
            "key_features": {},
            "risk_flags": {},
            "similar_cases": [],
        }
    )
    current_state["news_summary"] = build_research_news_summary(news_summary_items)

    return {
        "stock": {
            "stock_code": snapshot.stock.stock_code,
            "stock_name": snapshot.stock.stock_name,
            "market": snapshot.stock.market,
            "industry": snapshot.stock.industry,
            "concept_tags": snapshot.stock.concept_tags or [],
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
            for row in snapshot.prices
        ],
        "auto_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in snapshot.auto_points
        ],
        "final_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in snapshot.final_points
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
            for row in snapshot.trade_markers
        ],
        "news_items": news_items,
        "current_state": current_state,
    }


def build_research_news_summary(items: list[dict[str, object]]) -> dict[str, float]:
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
        "avg_adjusted_sentiment": round(sum(adjusted_scores) / len(adjusted_scores), 4)
        if adjusted_scores
        else 0.0,
        "positive_event_count": float(positive_event_count),
        "negative_event_count": float(negative_event_count),
        "governance_event_count": float(governance_event_count),
    }


def _resolve_news_category(*, raw: NewsRaw, processed: NewsProcessed | None) -> str | None:
    if processed is not None and processed.category is not None:
        return processed.category
    if raw.source_type in {"announcement", "media_news"}:
        return raw.source_type
    return None


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
