from __future__ import annotations

from collections.abc import Sequence

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.segment import SwingSegment


def average(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def compute_technical_features(segment: SwingSegment, price_rows: list[DailyPrice]) -> dict[str, float]:
    closes = [float(row.close_price) for row in price_rows]
    volumes = [float(row.volume or 0) for row in price_rows]

    ma5 = average(closes[-5:])
    ma20 = average(closes[-20:]) if len(closes) >= 20 else average(closes)
    start_close = closes[0] if closes else float(segment.start_price)
    end_close = closes[-1] if closes else float(segment.end_price)

    features = {
        "pct_change": float(segment.pct_change or 0),
        "duration_days": float(segment.duration_days or 0),
        "max_drawdown_pct": float(segment.max_drawdown_pct or 0),
        "volume_ratio_5d": (volumes[-1] / average(volumes[-5:])) if volumes and average(volumes[-5:]) else 0.0,
        "ma5_above_ma20": 1.0 if ma5 >= ma20 else 0.0,
        "macd_cross_flag": 1.0 if end_close > start_close else 0.0,
    }
    return features
