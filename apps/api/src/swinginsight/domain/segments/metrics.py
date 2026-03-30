from __future__ import annotations

from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint


def round_metric(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 4)


def compute_segment_metrics(
    *,
    start: DetectedTurningPoint,
    end: DetectedTurningPoint,
    price_window: list[dict[str, object]],
) -> dict[str, float | int]:
    pct_change = ((end.point_price - start.point_price) / start.point_price) * 100
    duration_days = (end.point_date - start.point_date).days
    trading_days = len(price_window)
    avg_daily_change_pct = pct_change / trading_days if trading_days else pct_change

    high_prices = [float(row["high_price"]) for row in price_window if row.get("high_price") is not None]
    low_prices = [float(row["low_price"]) for row in price_window if row.get("low_price") is not None]

    max_upside_pct = None
    max_drawdown_pct = None
    max_rebound_pct = None
    if high_prices:
        max_upside_pct = ((max(high_prices) - start.point_price) / start.point_price) * 100
        max_rebound_pct = ((max(high_prices) - end.point_price) / end.point_price) * 100
    if low_prices:
        max_drawdown_pct = ((min(low_prices) - start.point_price) / start.point_price) * 100

    return {
        "pct_change": round_metric(pct_change),
        "duration_days": duration_days,
        "max_upside_pct": round_metric(max_upside_pct),
        "max_drawdown_pct": round_metric(max_drawdown_pct),
        "max_rebound_pct": round_metric(max_rebound_pct),
        "avg_daily_change_pct": round_metric(avg_daily_change_pct),
    }
