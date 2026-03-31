from __future__ import annotations


def classify_current_state(features: dict[str, float]) -> str:
    pct_change = features.get("pct_change", 0.0)
    volume_ratio = features.get("volume_ratio_5d", 0.0)
    positive_news_ratio = features.get("positive_news_ratio", 0.0)
    max_drawdown = features.get("max_drawdown_pct", 0.0)

    if pct_change < 0:
        return "底部构建中"
    if pct_change >= 18 and volume_ratio >= 1.2:
        return "主升初期"
    if pct_change >= 8 and positive_news_ratio >= 0.5:
        return "启动前夕"
    if pct_change >= 12 and max_drawdown <= -8:
        return "高位震荡"
    return "疑似见顶"
