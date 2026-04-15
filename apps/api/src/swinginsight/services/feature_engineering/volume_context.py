from __future__ import annotations

from statistics import mean

from swinginsight.db.models.market_data import DailyPrice


def compute_volume_context_features(*, window_rows: list[DailyPrice], pre_rows: list[DailyPrice]) -> dict[str, float]:
    if len(window_rows) < 3 or len(pre_rows) < 10:
        return {}
    window_volumes = [float(row.volume or 0.0) for row in window_rows]
    baseline_volumes = [float(row.volume or 0.0) for row in pre_rows[-20:]]
    vol_ma20 = mean(baseline_volumes) if baseline_volumes else 0.0
    window_vol_avg = mean(window_volumes) if window_volumes else 0.0

    returns = _returns(window_rows)
    vol_price_corr = _pearson(window_volumes, returns) if len(window_volumes) >= 5 else 0.0

    return {
        "vol_ratio_vs_ma20": round(window_vol_avg / vol_ma20, 6) if vol_ma20 > 0 else 0.0,
        "vol_trend_tail": round(mean(window_volumes[-3:]) / window_vol_avg, 6) if window_vol_avg > 0 else 0.0,
        "vol_up_down_ratio": round(_up_down_vol_ratio(window_volumes, returns), 6),
        "vol_price_corr": round(vol_price_corr, 6),
    }


def _returns(rows: list[DailyPrice]) -> list[float]:
    values: list[float] = []
    previous_close: float | None = None
    for row in rows:
        close_price = float(row.close_price or 0.0)
        if previous_close is None or previous_close == 0:
            values.append(0.0)
        else:
            values.append(close_price / previous_close - 1.0)
        previous_close = close_price
    return values


def _up_down_vol_ratio(volumes: list[float], returns: list[float]) -> float:
    up = [volume for volume, ret in zip(volumes, returns, strict=False) if ret > 0]
    down = [volume for volume, ret in zip(volumes, returns, strict=False) if ret < 0]
    if not down:
        return 1.0
    return (mean(up) if up else 0.0) / mean(down)


def _pearson(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0
    mean_x = sum(xs) / len(xs)
    mean_y = sum(ys) / len(ys)
    cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
    var_x = sum((x - mean_x) ** 2 for x in xs)
    var_y = sum((y - mean_y) ** 2 for y in ys)
    denom = (var_x * var_y) ** 0.5
    if denom == 0:
        return 0.0
    return cov / denom
