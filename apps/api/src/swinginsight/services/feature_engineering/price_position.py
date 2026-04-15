from __future__ import annotations

from swinginsight.db.models.market_data import DailyPrice


def compute_price_position_features(*, history_rows: list[DailyPrice]) -> dict[str, float]:
    lookback = history_rows[-60:]
    if len(lookback) < 20:
        return {}

    closes = [float(row.close_price or 0.0) for row in lookback]
    close_now = closes[-1]
    high_60 = max(closes)
    low_60 = min(closes)
    range_60 = high_60 - low_60
    ma20 = sum(closes[-20:]) / 20

    return {
        "price_percentile_60d": round((close_now - low_60) / range_60, 6) if range_60 > 0 else 0.5,
        "drawdown_from_peak_60d": round((close_now - high_60) / high_60, 6) if high_60 > 0 else 0.0,
        "price_vs_ma20": round(close_now / ma20 - 1.0, 6) if ma20 > 0 else 0.0,
    }
