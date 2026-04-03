from __future__ import annotations

from statistics import mean

from swinginsight.db.models.market_data import DailyPrice


MIN_HISTORY_BARS = 21
WINDOW_SIZE = 7


def build_pattern_features(*, window_rows: list[DailyPrice], history_rows: list[DailyPrice]) -> dict[str, object] | None:
    if len(window_rows) != WINDOW_SIZE or len(history_rows) < MIN_HISTORY_BARS:
        return None

    closes = [float(row.close_price or 0) for row in window_rows]
    highs = [float(row.high_price or row.close_price or 0) for row in window_rows]
    lows = [float(row.low_price or row.close_price or 0) for row in window_rows]
    volumes = [float(row.volume or 0) for row in window_rows]
    turnover_rates = [float(row.turnover_rate or 0) for row in window_rows]
    anchor_close = closes[0] or 1.0

    price_seq = [close / anchor_close for close in closes]
    return_seq = [0.0]
    for index in range(1, len(closes)):
        prev_close = closes[index - 1] or 1.0
        return_seq.append(closes[index] / prev_close - 1.0)

    candle_feat: list[float] = []
    bull_flags: list[int] = []
    for row in window_rows:
        open_price = float(row.open_price or row.close_price or 0)
        high_price = float(row.high_price or row.close_price or 0)
        low_price = float(row.low_price or row.close_price or 0)
        close_price = float(row.close_price or 0)
        span = max(high_price - low_price, 1e-6)
        body = abs(close_price - open_price)
        upper_shadow = max(high_price - max(open_price, close_price), 0.0)
        lower_shadow = max(min(open_price, close_price) - low_price, 0.0)
        close_pos = (close_price - low_price) / span
        bull = 1 if close_price >= open_price else 0
        candle_feat.extend([body / span, upper_shadow / span, lower_shadow / span, close_pos, float(bull)])
        bull_flags.append(bull)

    avg_volume = mean(volumes) or 1.0
    avg_turnover = mean(turnover_rates) or 1.0
    volume_seq = [volume / avg_volume for volume in volumes]
    turnover_seq = [turnover / avg_turnover for turnover in turnover_rates]

    history_closes = [float(row.close_price or 0) for row in history_rows]
    ma5 = _moving_average(history_closes, 5)
    ma10 = _moving_average(history_closes, 10)
    ma20 = _moving_average(history_closes, 20)
    ma60 = _moving_average(history_closes, 60)
    if None in {ma5, ma10, ma20, ma60}:
        return None

    slope_ma5 = _moving_average_slope(history_closes, 5)
    slope_ma10 = _moving_average_slope(history_closes, 10)
    slope_ma20 = _moving_average_slope(history_closes, 20)

    trend_label = _trend_label(ma5=ma5 or 0, ma10=ma10 or 0, ma20=ma20 or 0, slope_ma10=slope_ma10)
    trend_context = [
        (closes[-1] / (ma5 or closes[-1])) if ma5 else 1.0,
        (closes[-1] / (ma10 or closes[-1])) if ma10 else 1.0,
        (closes[-1] / (ma20 or closes[-1])) if ma20 else 1.0,
        (closes[-1] / (ma60 or closes[-1])) if ma60 else 1.0,
        slope_ma5,
        slope_ma10,
        slope_ma20,
        1.0 if trend_label == "uptrend" else 0.0,
        1.0 if trend_label == "sideways" else 0.0,
        1.0 if trend_label == "downtrend" else 0.0,
    ]

    atr5 = _atr(history_rows, 5)
    atr10 = _atr(history_rows, 10)
    if atr5 is None or atr10 is None:
        return None
    amp = (max(highs) - min(lows)) / anchor_close if anchor_close else 0.0
    intraday_amps = [(high - low) / (close or 1.0) for high, low, close in zip(highs, lows, closes, strict=False)]
    vola_context = [
        atr5 / anchor_close if anchor_close else 0.0,
        atr10 / anchor_close if anchor_close else 0.0,
        amp,
        mean(intraday_amps) if intraday_amps else 0.0,
        max(intraday_amps) if intraday_amps else 0.0,
    ]

    highest_day_pos = highs.index(max(highs))
    lowest_day_pos = lows.index(min(lows))
    coarse_vector = return_seq + volume_seq + [float(flag) for flag in bull_flags]
    return {
        "price_seq": price_seq,
        "return_seq": return_seq,
        "candle_feat": candle_feat,
        "bull_flags": bull_flags,
        "volume_seq": volume_seq,
        "turnover_seq": turnover_seq,
        "trend_context": trend_context,
        "vola_context": vola_context,
        "coarse_vector": coarse_vector,
        "highest_day_pos": highest_day_pos,
        "lowest_day_pos": lowest_day_pos,
        "trend_label": trend_label,
    }


def _moving_average(values: list[float], window: int) -> float | None:
    if not values:
        return None
    size = min(len(values), window)
    chunk = values[-size:]
    if not chunk:
        return None
    return sum(chunk) / size


def _moving_average_slope(values: list[float], window: int) -> float:
    if len(values) < 2:
        return 0.0
    size = min(len(values), window)
    if len(values) <= size:
        previous = values[:-1]
        current = values[-size:]
    else:
        current = values[-size:]
        previous = values[-size - 1 : -1]
    if not previous or not current:
        return 0.0
    current_avg = sum(current) / len(current)
    previous_avg = sum(previous) / len(previous)
    if previous_avg == 0:
        return 0.0
    return current_avg / previous_avg - 1.0


def _trend_label(*, ma5: float, ma10: float, ma20: float, slope_ma10: float) -> str:
    if ma5 > ma10 > ma20 and slope_ma10 > 0:
        return "uptrend"
    if ma5 < ma10 < ma20 and slope_ma10 < 0:
        return "downtrend"
    return "sideways"


def _atr(rows: list[DailyPrice], window: int) -> float | None:
    if not rows:
        return None
    size = min(len(rows), window)
    sample = rows[-size:]
    if not sample:
        return None
    reference_index = max(len(rows) - size - 1, 0)
    previous_close = float(rows[reference_index].close_price or sample[0].close_price or 0)
    true_ranges: list[float] = []
    for row in sample:
        high_price = float(row.high_price or row.close_price or 0)
        low_price = float(row.low_price or row.close_price or 0)
        close_price = float(row.close_price or 0)
        true_ranges.append(max(high_price - low_price, abs(high_price - previous_close), abs(low_price - previous_close)))
        previous_close = close_price
    return sum(true_ranges) / len(true_ranges) if true_ranges else None
