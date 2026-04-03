from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(slots=True, frozen=True)
class EventSignal:
    sentence_index: int
    sentence_text: str
    event_type: str
    event_polarity: str
    event_strength: int
    trigger_keywords: list[str]


@dataclass(slots=True, frozen=True)
class EventRule:
    keywords: tuple[str, ...]
    event_type: str
    event_polarity: str
    event_strength: int


EVENT_RULES: tuple[EventRule, ...] = (
    EventRule(("业绩预增", "预增", "扭亏", "业绩快报", "净利润增长", "净利润同比增长"), "earnings", "positive", 4),
    EventRule(("预亏", "亏损", "下修", "业绩下滑"), "earnings", "negative", 4),
    EventRule(("回购", "增持"), "capital_action", "positive", 3),
    EventRule(("减持",), "capital_action", "negative", 3),
    EventRule(("重组终止", "终止收购", "终止重组"), "mna", "negative", 4),
    EventRule(("重组", "收购", "并购", "资产置换"), "mna", "positive", 4),
    EventRule(("风险提示", "异常波动", "问询", "处罚", "立案", "诉讼"), "risk_alert", "negative", 4),
    EventRule(("中标", "订单", "签署", "协议"), "order_contract", "positive", 3),
    EventRule(("补贴", "获批", "批复", "政策支持", "落地"), "policy_catalyst", "positive", 3),
    EventRule(
        ("董事会决议", "会议决议", "股东大会决议", "股东大会通知", "股东会通知", "股东会的通知", "股东会材料", "工作规则"),
        "governance",
        "neutral",
        1,
    ),
)


def extract_events(title: str, summary: str | None = None) -> list[EventSignal]:
    signals: list[EventSignal] = []
    seen: set[tuple[int, str, str]] = set()

    for sentence_index, sentence_text in enumerate(_split_sentences(title, summary)):
        for rule in EVENT_RULES:
            matched_keywords = [keyword for keyword in rule.keywords if keyword in sentence_text]
            if not matched_keywords:
                continue
            dedupe_key = (sentence_index, rule.event_type, rule.event_polarity)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)
            signals.append(
                EventSignal(
                    sentence_index=sentence_index,
                    sentence_text=sentence_text,
                    event_type=rule.event_type,
                    event_polarity=rule.event_polarity,
                    event_strength=rule.event_strength,
                    trigger_keywords=matched_keywords,
                )
            )

    return signals


def _split_sentences(title: str, summary: str | None = None) -> list[str]:
    source_parts = [title]
    if summary:
        source_parts.append(summary)

    segments: list[str] = []
    for part in source_parts:
        for segment in re.split(r"[，,；;。！？!?]\s*", part):
            cleaned = segment.strip()
            if cleaned:
                segments.append(cleaned)
    return segments
