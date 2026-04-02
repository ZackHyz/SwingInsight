from __future__ import annotations

from math import exp, log, log1p, sqrt


FEATURE_WEIGHTS = {
    "pct_change": 1.8,
    "max_drawdown_pct": 1.6,
    "duration_days": 0.8,
    "volume_ratio_5d": 1.2,
    "avg_volume_5d": 1.1,
    "avg_volume_10d": 1.1,
    "avg_turnover_rate_5d": 1.1,
    "avg_turnover_rate_10d": 1.1,
    "positive_news_ratio": 0.8,
    "duplicate_news_ratio": 0.5,
    "ma5_above_ma20": 0.6,
    "macd_cross_flag": 0.6,
}

PRICE_FEATURES = (
    "pct_change",
    "max_drawdown_pct",
)

VOLUME_FEATURES = (
    "volume_ratio_5d",
    "avg_volume_5d",
    "avg_volume_10d",
)

TURNOVER_FEATURES = (
    "avg_turnover_rate_5d",
    "avg_turnover_rate_10d",
)

PATTERN_FEATURES = (
    "duration_days",
    "ma5_above_ma20",
    "macd_cross_flag",
)

PRICE_COMPONENT_WEIGHT = 0.48
VOLUME_COMPONENT_WEIGHT = 0.12
TURNOVER_COMPONENT_WEIGHT = 0.05
PATTERN_COMPONENT_WEIGHT = 0.35


def build_standardized_vectors(vectors: list[dict[str, float]]) -> list[dict[str, float]]:
    if not vectors:
        return []
    keys = sorted(set().union(*(vector.keys() for vector in vectors)))
    transformed_vectors = [{key: _transform_feature_value(key, vector.get(key, 0.0)) for key in keys} for vector in vectors]
    stats: dict[str, tuple[float, float]] = {}
    for key in keys:
        values = [vector[key] for vector in transformed_vectors]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        stats[key] = (mean, sqrt(variance))

    standardized: list[dict[str, float]] = []
    for vector in transformed_vectors:
        standardized.append(
            {
                key: ((vector[key] - stats[key][0]) / stats[key][1] if stats[key][1] > 1e-9 else 0.0) * FEATURE_WEIGHTS.get(key, 1.0)
                for key in keys
            }
        )
    return standardized


def _transform_feature_value(key: str, value: float) -> float:
    if key.startswith("avg_volume_"):
        return log1p(max(value, 0.0))
    if key.startswith("avg_turnover_rate_"):
        return log1p(max(value, 0.0))
    if key == "duration_days":
        return log1p(max(value, 0.0))
    return value


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    keys = sorted(set(left) | set(right))
    numerator = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in keys)
    left_norm = sqrt(sum(left.get(key, 0.0) ** 2 for key in keys))
    right_norm = sqrt(sum(right.get(key, 0.0) ** 2 for key in keys))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def component_similarity(left: dict[str, float], right: dict[str, float], feature_names: tuple[str, ...]) -> float:
    left_subset = {key: left.get(key, 0.0) for key in feature_names}
    right_subset = {key: right.get(key, 0.0) for key in feature_names}
    raw_score = cosine_similarity(left_subset, right_subset)
    return round(max(0.0, min(1.0, (raw_score + 1.0) / 2.0)), 4)


def blend_scores(*pairs: tuple[float, float]) -> float:
    total_weight = sum(weight for weight, _ in pairs) or 1.0
    total_score = sum(weight * score for weight, score in pairs)
    return round(max(0.0, min(1.0, total_score / total_weight)), 4)


def sequence_similarity(left: list[float], right: list[float], scale: float = 6.0) -> float:
    if not left or not right:
        return 0.0
    size = min(len(left), len(right))
    if size == 0:
        return 0.0
    mean_abs_diff = sum(abs(left[index] - right[index]) for index in range(size)) / size
    return round(max(0.0, min(1.0, exp(-scale * mean_abs_diff))), 4)


def _resample_series(values: list[float], points: int) -> list[float]:
    if not values:
        return []
    if len(values) == 1:
        return [values[0]] * points

    result: list[float] = []
    last_index = len(values) - 1
    for point_index in range(points):
        position = point_index * last_index / max(points - 1, 1)
        left_index = int(position)
        right_index = min(left_index + 1, last_index)
        if left_index == right_index:
            result.append(values[left_index])
            continue
        weight = position - left_index
        result.append(values[left_index] * (1.0 - weight) + values[right_index] * weight)
    return result


def trajectory_similarity(left: list[float], right: list[float], *, points: int = 12, scale: float = 5.0) -> float:
    if not left or not right:
        return 0.0
    return sequence_similarity(_resample_series(left, points), _resample_series(right, points), scale=scale)


def bar_count_similarity(left_count: int, right_count: int, scale: float = 2.2) -> float:
    if left_count <= 0 or right_count <= 0:
        return 0.0
    if left_count == right_count:
        return 1.0
    gap = abs(log(right_count / left_count))
    return round(max(0.0, min(1.0, exp(-scale * gap))), 4)
