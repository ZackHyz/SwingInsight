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
    signal_source: str = "media"
    confidence: float = 0.5


@dataclass(slots=True, frozen=True)
class EventRule:
    keywords: tuple[str, ...]
    event_type: str
    event_polarity: str
    event_strength: int
    source_channels: tuple[str, ...] = ("announcement", "media", "rumor")
    base_confidence: float = 0.7


EVENT_RULES: tuple[EventRule, ...] = (
    EventRule(("业绩预增", "预增", "扭亏", "业绩快报", "净利润增长", "净利润同比增长"), "earnings", "positive", 4, base_confidence=0.85),
    EventRule(("预亏", "亏损", "下修", "业绩下滑"), "earnings", "negative", 4, base_confidence=0.85),
    EventRule(("回购", "增持"), "capital_action", "positive", 3, base_confidence=0.8),
    EventRule(("减持",), "capital_action", "negative", 3, base_confidence=0.8),
    EventRule(("重组终止", "终止收购", "终止重组"), "mna", "negative", 4, base_confidence=0.8),
    EventRule(("重组", "收购", "并购", "资产置换"), "mna", "positive", 4, base_confidence=0.8),
    EventRule(("风险提示", "异常波动", "问询", "处罚", "立案", "诉讼"), "risk_alert", "negative", 4, base_confidence=0.7),
    EventRule(("中标", "订单", "签署", "协议"), "order_contract", "positive", 3, base_confidence=0.8),
    EventRule(("补贴", "获批", "批复", "政策支持", "落地"), "policy_catalyst", "positive", 3, base_confidence=0.75),
    EventRule(
        ("董事会决议", "会议决议", "股东大会决议", "股东大会通知", "股东会通知", "股东会的通知", "股东会材料", "工作规则"),
        "governance",
        "neutral",
        1,
        source_channels=("announcement", "media"),
        base_confidence=0.7,
    ),
)

SOURCE_CONFIDENCE_MULTIPLIER = {
    "announcement": 1.0,
    "media": 0.8,
    "rumor": 0.65,
}

RUMOR_HINT_KEYWORDS: tuple[str, ...] = ("传闻", "网传", "据悉", "坊间")
GOVERNANCE_TEMPLATE_HINTS: tuple[str, ...] = ("通知", "材料", "会议决议", "股东会")
SUPPRESSIBLE_RISK_KEYWORDS: tuple[str, ...] = ("风险提示", "异常波动")


def extract_events(title: str, summary: str | None = None, source_type: str | None = None) -> list[EventSignal]:
    signals: list[EventSignal] = []
    seen: set[tuple[int, str, str]] = set()
    signal_source = _resolve_signal_source(title=title, summary=summary, source_type=source_type)

    for sentence_index, sentence_text in enumerate(_split_sentences(title, summary)):
        for rule in EVENT_RULES:
            if signal_source not in rule.source_channels:
                continue
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
                    signal_source=signal_source,
                    confidence=round(
                        min(rule.base_confidence * SOURCE_CONFIDENCE_MULTIPLIER.get(signal_source, 0.7), 0.99),
                        4,
                    ),
                )
            )

    return _suppress_governance_template_noise(signals)


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


def _resolve_signal_source(*, title: str, summary: str | None, source_type: str | None) -> str:
    if source_type == "announcement":
        return "announcement"

    corpus = f"{title} {summary or ''}"
    if any(keyword in corpus for keyword in RUMOR_HINT_KEYWORDS):
        return "rumor"
    return "media"


def _suppress_governance_template_noise(signals: list[EventSignal]) -> list[EventSignal]:
    if not signals:
        return signals

    if signals[0].signal_source != "announcement":
        return signals

    governance_events = [event for event in signals if event.event_type == "governance"]
    if not governance_events:
        return signals

    has_template = any(any(hint in event.sentence_text for hint in GOVERNANCE_TEMPLATE_HINTS) for event in governance_events)
    if not has_template:
        return signals

    non_governance_events = [event for event in signals if event.event_type != "governance"]
    if not non_governance_events:
        return signals

    suppressible_only = all(
        event.event_type == "risk_alert"
        and all(keyword in SUPPRESSIBLE_RISK_KEYWORDS for keyword in event.trigger_keywords)
        for event in non_governance_events
    )
    if not suppressible_only:
        return signals

    return [
        EventSignal(
            sentence_index=event.sentence_index,
            sentence_text=event.sentence_text,
            event_type="governance",
            event_polarity="neutral",
            event_strength=event.event_strength,
            trigger_keywords=event.trigger_keywords,
            signal_source=event.signal_source,
            confidence=min(event.confidence, 0.6),
        )
        for event in governance_events
    ]
