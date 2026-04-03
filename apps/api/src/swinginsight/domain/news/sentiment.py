from __future__ import annotations

from dataclasses import dataclass

from swinginsight.domain.news.events import EventSignal, extract_events


POLARITY_WEIGHTS = {
    "positive": 1.0,
    "neutral": 0.0,
    "negative": -1.0,
}


@dataclass(slots=True, frozen=True)
class NewsSentimentScore:
    sentiment_label: str
    sentiment_score_base: float
    sentiment_score_adjusted: float
    confidence_score: float
    heat_score: float
    market_context_score: float
    position_context_score: float
    event_conflict_flag: bool
    event_types: list[str]
    model_version: str


def score_news_sentiment(
    *,
    title: str,
    summary: str | None,
    source_type: str | None,
    duplicate_count: int,
    events: list[EventSignal] | None = None,
) -> NewsSentimentScore:
    resolved_events = events if events is not None else extract_events(title, summary)
    base_score = _compute_base_score(resolved_events)
    conflict = _has_conflicting_events(resolved_events)
    confidence = _compute_confidence_score(resolved_events, source_type=source_type)
    heat_score = _compute_heat_score(duplicate_count=duplicate_count, source_type=source_type, event_count=len(resolved_events))

    return NewsSentimentScore(
        sentiment_label=_label_from_score(base_score),
        sentiment_score_base=base_score,
        sentiment_score_adjusted=base_score,
        confidence_score=confidence,
        heat_score=heat_score,
        market_context_score=0.0,
        position_context_score=0.0,
        event_conflict_flag=conflict,
        event_types=list(dict.fromkeys(event.event_type for event in resolved_events)),
        model_version="rules:v1",
    )


def _compute_base_score(events: list[EventSignal]) -> float:
    if not events:
        return 0.0
    raw_score = sum((event.event_strength / 5.0) * POLARITY_WEIGHTS.get(event.event_polarity, 0.0) for event in events)
    return round(raw_score / len(events), 4)


def _has_conflicting_events(events: list[EventSignal]) -> bool:
    polarities = {event.event_polarity for event in events}
    return "positive" in polarities and "negative" in polarities


def _compute_confidence_score(events: list[EventSignal], *, source_type: str | None) -> float:
    if not events:
        return 0.25
    base = 0.55 + min(len(events), 3) * 0.1
    if source_type == "announcement":
        base += 0.05
    return min(round(base, 4), 0.95)


def _compute_heat_score(*, duplicate_count: int, source_type: str | None, event_count: int) -> float:
    score = 0.35
    if source_type == "announcement":
        score += 0.25
    if duplicate_count > 1:
        score += 0.25
    if event_count > 1:
        score += 0.1
    return min(round(score, 4), 1.0)


def _label_from_score(score: float) -> str:
    if score >= 0.25:
        return "positive"
    if score <= -0.25:
        return "negative"
    return "neutral"
