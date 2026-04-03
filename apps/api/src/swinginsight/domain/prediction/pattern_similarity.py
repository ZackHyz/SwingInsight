from __future__ import annotations

from math import exp, sqrt


def calc_pattern_similarity(query_features: dict[str, object], sample_features: dict[str, object]) -> dict[str, float]:
    price_score = sim_price(query_features["price_seq"], sample_features["price_seq"])
    candle_score = sim_candle(query_features, sample_features)
    volume_score = sim_volume(query_features["volume_seq"], sample_features["volume_seq"])
    turnover_score = sim_turnover(query_features["turnover_seq"], sample_features["turnover_seq"])
    trend_score = sim_trend(query_features["trend_context"], sample_features["trend_context"])
    vola_score = sim_vola(query_features["vola_context"], sample_features["vola_context"])
    total = (
        0.35 * price_score
        + 0.25 * candle_score
        + 0.15 * volume_score
        + 0.08 * turnover_score
        + 0.12 * trend_score
        + 0.05 * vola_score
    )
    return {
        "total_similarity": _clamp(total),
        "sim_price": price_score,
        "sim_candle": candle_score,
        "sim_volume": volume_score,
        "sim_turnover": turnover_score,
        "sim_trend": trend_score,
        "sim_vola": vola_score,
    }


def sim_price(left: list[float], right: list[float], scale: float = 8.0) -> float:
    return _clamp(exp(-scale * _dtw_distance(left, right)))


def sim_candle(left: dict[str, object], right: dict[str, object]) -> float:
    candle_cos = _cosine_similarity(_as_floats(left["candle_feat"]), _as_floats(right["candle_feat"]))
    bull_left = list(left.get("bull_flags", []))
    bull_right = list(right.get("bull_flags", []))
    if bull_left and bull_right:
        pairs = min(len(bull_left), len(bull_right))
        bull_match = sum(1 for index in range(pairs) if bull_left[index] == bull_right[index]) / pairs
    else:
        bull_match = 0.0

    turning_left_high = int(left.get("highest_day_pos", 0))
    turning_right_high = int(right.get("highest_day_pos", 0))
    turning_left_low = int(left.get("lowest_day_pos", 0))
    turning_right_low = int(right.get("lowest_day_pos", 0))
    max_gap = max(max(len(bull_left), len(bull_right)) - 1, 1)
    turning_match = (
        1.0 - abs(turning_left_high - turning_right_high) / max_gap
        + 1.0 - abs(turning_left_low - turning_right_low) / max_gap
    ) / 2.0
    return _clamp(0.8 * candle_cos + 0.1 * bull_match + 0.1 * turning_match)


def sim_volume(left: list[float], right: list[float]) -> float:
    cosine = _cosine_similarity(left, right)
    pearson = _pearson_similarity(left, right)
    return _clamp(0.6 * cosine + 0.4 * pearson)


def sim_turnover(left: list[float], right: list[float]) -> float:
    cosine = _cosine_similarity(left, right)
    pearson = _pearson_similarity(left, right)
    return _clamp(0.7 * cosine + 0.3 * pearson)


def sim_trend(left: list[float], right: list[float]) -> float:
    return _cosine_similarity(left, right)


def sim_vola(left: list[float], right: list[float], beta: float = 4.0) -> float:
    return _clamp(exp(-beta * _euclidean_distance(left, right)))


def _dtw_distance(left: list[float], right: list[float]) -> float:
    if not left or not right:
        return 1.0
    rows = len(left)
    cols = len(right)
    table = [[float("inf")] * (cols + 1) for _ in range(rows + 1)]
    table[0][0] = 0.0
    for i in range(1, rows + 1):
        for j in range(1, cols + 1):
            cost = abs(left[i - 1] - right[j - 1])
            table[i][j] = cost + min(table[i - 1][j], table[i][j - 1], table[i - 1][j - 1])
    return table[rows][cols] / max(rows, cols)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    left = left[:size]
    right = right[:size]
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = sqrt(sum(a * a for a in left))
    right_norm = sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    raw = numerator / (left_norm * right_norm)
    return _clamp((raw + 1.0) / 2.0)


def _pearson_similarity(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    left = left[:size]
    right = right[:size]
    mean_left = sum(left) / size
    mean_right = sum(right) / size
    numerator = sum((a - mean_left) * (b - mean_right) for a, b in zip(left, right, strict=False))
    denom_left = sqrt(sum((a - mean_left) ** 2 for a in left))
    denom_right = sqrt(sum((b - mean_right) ** 2 for b in right))
    if denom_left == 0 or denom_right == 0:
        return 1.0 if left == right else 0.0
    raw = numerator / (denom_left * denom_right)
    return _clamp((raw + 1.0) / 2.0)


def _euclidean_distance(left: list[float], right: list[float]) -> float:
    size = min(len(left), len(right))
    if size == 0:
        return 1.0
    return sqrt(sum((left[index] - right[index]) ** 2 for index in range(size)) / size)


def _as_floats(values: object) -> list[float]:
    return [float(value) for value in values] if isinstance(values, list) else []


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)
