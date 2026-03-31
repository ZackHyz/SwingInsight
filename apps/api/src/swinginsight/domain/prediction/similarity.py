from __future__ import annotations

from math import sqrt


def cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    keys = sorted(set(left) | set(right))
    numerator = sum(left.get(key, 0.0) * right.get(key, 0.0) for key in keys)
    left_norm = sqrt(sum(left.get(key, 0.0) ** 2 for key in keys))
    right_norm = sqrt(sum(right.get(key, 0.0) ** 2 for key in keys))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)
