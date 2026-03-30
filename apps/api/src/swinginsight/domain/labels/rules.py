from __future__ import annotations


def derive_labels(*, technical: dict[str, float], news: dict[str, float]) -> list[tuple[str, float]]:
    labels: list[tuple[str, float]] = []
    if technical.get("volume_ratio_5d", 0) >= 1.2 and technical.get("pct_change", 0) > 0:
        labels.append(("放量突破型", 0.9))
    if news.get("positive_news_ratio", 0) >= 0.5:
        labels.append(("消息刺激型", 0.8))
    if technical.get("volume_ratio_5d", 0) < 1.0 and technical.get("pct_change", 0) > 0:
        labels.append(("缩量筑底型", 0.6))
    if technical.get("pct_change", 0) < 0:
        labels.append(("高位见顶型", 0.8))
    return labels
