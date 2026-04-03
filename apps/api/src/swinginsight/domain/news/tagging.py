from __future__ import annotations

from dataclasses import dataclass

from swinginsight.domain.news.sentiment import NewsSentimentScore, score_news_sentiment


@dataclass(slots=True, frozen=True)
class NewsTags:
    sentiment: str
    heat_level: str
    tag_list: list[str]


def build_tags(
    *,
    title: str,
    summary: str | None = None,
    source_type: str | None,
    duplicate_count: int,
    sentiment_result: NewsSentimentScore | None = None,
) -> NewsTags:
    resolved_sentiment = sentiment_result or score_news_sentiment(
        title=title,
        summary=summary,
        source_type=source_type,
        duplicate_count=duplicate_count,
    )
    heat_level = "low"
    if resolved_sentiment.heat_score >= 0.75:
        heat_level = "high"
    elif resolved_sentiment.heat_score >= 0.45:
        heat_level = "medium"
    tags = ["official" if source_type == "announcement" else "follow_up"]
    tags.append("repeated_spread" if duplicate_count > 1 else "first_release")
    if resolved_sentiment.event_conflict_flag:
        tags.append("conflicting_events")

    return NewsTags(sentiment=resolved_sentiment.sentiment_label, heat_level=heat_level, tag_list=tags)
