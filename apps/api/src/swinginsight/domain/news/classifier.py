from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class NewsClassification:
    category: str
    sub_category: str | None
    keywords: list[str]


RULES: list[tuple[tuple[str, ...], str, str | None]] = [
    (("业绩预告", "净利润", "扭亏", "业绩快报"), "announcement", "earnings"),
    (("回购", "增持", "减持"), "announcement", "capital_action"),
    (("重组", "收购", "资产置换", "并购"), "announcement", "mna"),
    (("风险提示", "异常波动"), "announcement", "risk_alert"),
    (
        (
            "董事会决议",
            "会议决议",
            "股东大会决议",
            "股东大会通知",
            "股东会通知",
            "股东会的通知",
            "股东会材料",
            "工作规则",
        ),
        "announcement",
        "governance",
    ),
    (("订单", "协议", "中标"), "media_news", "order_contract"),
    (("政策支持", "补贴", "获批", "批复", "落地"), "media_news", "policy_catalyst"),
]


def classify_title(title: str, source_type: str | None = None) -> NewsClassification:
    matched_keywords: list[str] = []
    for keywords, category, sub_category in RULES:
        current_matches = [keyword for keyword in keywords if keyword in title]
        if not current_matches:
            continue
        matched_keywords.extend(current_matches)
        return NewsClassification(category=category, sub_category=sub_category, keywords=matched_keywords)

    if source_type == "announcement":
        return NewsClassification(category="announcement", sub_category=None, keywords=matched_keywords)

    return NewsClassification(category="media_news", sub_category=None, keywords=matched_keywords)
