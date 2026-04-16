from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import NewsEventResult, NewsRaw, NewsSentimentResult
from swinginsight.domain.news.events import EventSignal, extract_events
from swinginsight.domain.news.sentiment import NewsSentimentScore, score_news_sentiment

SENTIMENT_LABEL_SCORES = {
    "positive": 0.6,
    "neutral": 0.0,
    "negative": -0.6,
}

HEAT_LEVEL_SCORES = {
    "low": 0.3,
    "medium": 0.5,
    "high": 0.8,
}

POSITION_BULLISH_EVENTS = {"earnings", "policy_catalyst", "order_contract"}
POSITION_RISK_EVENTS = {"risk_alert", "capital_action"}
SOURCE_PRIORITY = {"rumor": 1, "media": 2, "announcement": 3}


@dataclass(slots=True, frozen=True)
class NewsSentimentPersistenceResult:
    sentiment_result_count: int
    event_result_count: int
    sentiment_score: NewsSentimentScore


def sentiment_label_to_score(sentiment_label: str | None) -> float:
    return SENTIMENT_LABEL_SCORES.get(sentiment_label or "", 0.0)


def heat_level_to_score(heat_level: str | None) -> float:
    return HEAT_LEVEL_SCORES.get(heat_level or "", 0.3)


def resolve_base_sentiment_score(base_score: object | None, sentiment_label: str | None) -> float:
    if base_score is None:
        return sentiment_label_to_score(sentiment_label)
    return round(float(base_score), 4)


def resolve_heat_score(heat_score: object | None, heat_level: str | None) -> float:
    if heat_score is None:
        return heat_level_to_score(heat_level)
    return round(float(heat_score), 4)


def adjust_sentiment_with_position(
    *,
    base_score: float,
    category: str | None,
    relation_type: str | None,
    point_type: str | None,
    heat_score: float,
    event_types: list[str] | None = None,
) -> float:
    adjusted = base_score
    event_type_set = set(event_types or [])

    if (
        relation_type == "before_trough"
        and adjusted > 0
        and category == "announcement"
        and event_type_set.intersection(POSITION_BULLISH_EVENTS)
    ):
        adjusted += 0.15

    if relation_type == "before_peak" and point_type == "peak" and adjusted > 0 and heat_score >= 0.6:
        adjusted -= 0.15

    if relation_type == "after_peak" and point_type == "peak" and (
        adjusted < 0 or event_type_set.intersection(POSITION_RISK_EVENTS)
    ):
        adjusted -= 0.2

    return round(max(min(adjusted, 1.0), -1.0), 4)


def merge_event_signals(events: list[EventSignal]) -> list[EventSignal]:
    grouped: dict[str, list[EventSignal]] = {}
    for event in events:
        grouped.setdefault(event.event_type, []).append(event)

    merged: list[EventSignal] = []
    for group_events in grouped.values():
        if len(group_events) == 1:
            merged.append(group_events[0])
            continue

        sorted_events = sorted(
            group_events,
            key=lambda event: (
                SOURCE_PRIORITY.get(event.signal_source, 0),
                event.confidence,
                event.event_strength,
            ),
            reverse=True,
        )
        top = sorted_events[0]
        second = sorted_events[1]
        has_polarity_conflict = len({event.event_polarity for event in sorted_events if event.event_polarity != "neutral"}) > 1
        close_confidence = abs(top.confidence - second.confidence) <= 0.03
        same_priority = SOURCE_PRIORITY.get(top.signal_source, 0) == SOURCE_PRIORITY.get(second.signal_source, 0)

        if has_polarity_conflict and close_confidence and same_priority:
            merged.append(
                EventSignal(
                    sentence_index=top.sentence_index,
                    sentence_text=top.sentence_text,
                    event_type=top.event_type,
                    event_polarity="neutral",
                    event_strength=top.event_strength,
                    trigger_keywords=sorted(set(top.trigger_keywords + second.trigger_keywords)),
                    signal_source=top.signal_source,
                    confidence=round(max(top.confidence, second.confidence), 4),
                )
            )
            continue

        merged.append(top)
    return merged


class NewsSentimentService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def persist_for_news(self, row: NewsRaw, *, duplicate_count: int) -> NewsSentimentPersistenceResult:
        events = merge_event_signals(extract_events(row.title, row.summary, source_type=row.source_type))
        sentiment_score = score_news_sentiment(
            title=row.title,
            summary=row.summary,
            source_type=row.source_type,
            duplicate_count=duplicate_count,
            events=events,
        )
        calculated_at = datetime.now(UTC).replace(tzinfo=None)

        existing_sentiment = self.session.scalar(
            select(NewsSentimentResult).where(NewsSentimentResult.news_id == row.id)
        )
        if existing_sentiment is None:
            existing_sentiment = NewsSentimentResult(news_id=row.id)
            self.session.add(existing_sentiment)

        existing_sentiment.stock_code = row.stock_code
        existing_sentiment.sentiment_label = sentiment_score.sentiment_label
        existing_sentiment.sentiment_score_base = sentiment_score.sentiment_score_base
        existing_sentiment.sentiment_score_adjusted = sentiment_score.sentiment_score_adjusted
        existing_sentiment.confidence_score = sentiment_score.confidence_score
        existing_sentiment.heat_score = sentiment_score.heat_score
        existing_sentiment.market_context_score = sentiment_score.market_context_score
        existing_sentiment.position_context_score = sentiment_score.position_context_score
        existing_sentiment.event_conflict_flag = sentiment_score.event_conflict_flag
        existing_sentiment.model_version = sentiment_score.model_version
        existing_sentiment.calculated_at = calculated_at

        self.session.execute(delete(NewsEventResult).where(NewsEventResult.news_id == row.id))
        for event in events:
            self.session.add(
                NewsEventResult(
                    news_id=row.id,
                    stock_code=row.stock_code,
                    sentence_index=event.sentence_index,
                    sentence_text=event.sentence_text,
                    event_type=event.event_type,
                    event_polarity=event.event_polarity,
                    event_strength=event.event_strength,
                    entity_main=row.stock_code,
                    entity_secondary=None,
                    trigger_keywords=event.trigger_keywords,
                    model_version=sentiment_score.model_version,
                )
            )

        return NewsSentimentPersistenceResult(
            sentiment_result_count=1,
            event_result_count=len(events),
            sentiment_score=sentiment_score,
        )
