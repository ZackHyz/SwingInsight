from __future__ import annotations

from swinginsight.db.models.market_data import DailyPrice


def compute_trend_context_features(*, pre_rows: list[DailyPrice]) -> dict[str, float]:
    sample = pre_rows[-20:]
    if len(sample) < 10:
        return {}
    closes = [float(row.close_price or 0.0) for row in sample]
    if closes[0] <= 0:
        return {}
    slope = _linear_slope(closes)
    mean_close = sum(closes) / len(closes)
    returns = [closes[i] / closes[i - 1] - 1.0 for i in range(1, len(closes)) if closes[i - 1] > 0]
    pre_return = closes[-1] / closes[0] - 1.0

    return {
        "pre_trend_slope_norm": round(slope / mean_close, 6) if mean_close > 0 else 0.0,
        "pre_return_20d": round(pre_return, 6),
        "pre_volatility_20d": round(_std(returns), 6) if returns else 0.0,
    }


def _linear_slope(values: list[float]) -> float:
    n = len(values)
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(values) / n
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, values, strict=False))
    denominator = sum((x - mean_x) ** 2 for x in xs)
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _std(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = sum(values) / len(values)
    variance = sum((value - avg) ** 2 for value in values) / (len(values) - 1)
    return variance**0.5
