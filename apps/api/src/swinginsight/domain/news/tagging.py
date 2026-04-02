from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NewsTags:
    sentiment: str
    heat_level: str
    tag_list: list[str]


POSITIVE_KEYWORDS = ("扭亏", "增长", "增持", "回购", "中标", "订单", "签署")
NEGATIVE_KEYWORDS = ("风险", "减持", "问询", "异常波动", "下滑", "亏损")


def build_tags(*, title: str, source_type: str | None, duplicate_count: int) -> NewsTags:
    sentiment = "neutral"
    if any(keyword in title for keyword in POSITIVE_KEYWORDS):
        sentiment = "positive"
    if any(keyword in title for keyword in NEGATIVE_KEYWORDS):
        sentiment = "negative"

    heat_level = "high" if duplicate_count > 1 or source_type == "announcement" else "medium"
    tags = ["official" if source_type == "announcement" else "follow_up"]
    tags.append("repeated_spread" if duplicate_count > 1 else "first_release")

    return NewsTags(sentiment=sentiment, heat_level=heat_level, tag_list=tags)
