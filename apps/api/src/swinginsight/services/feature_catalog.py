from __future__ import annotations

from swinginsight.db.models.pattern import PatternFeature


COARSE_FEATURE_NAMES = tuple(
    [f"ret_d{index}" for index in range(7)]
    + [f"vol_norm_d{index}" for index in range(7)]
    + [f"bull_flag_d{index}" for index in range(7)]
)

CONTEXT_FEATURE_NAMES = (
    "vol_ratio_vs_ma20",
    "vol_trend_tail",
    "vol_up_down_ratio",
    "vol_price_corr",
    "price_percentile_60d",
    "drawdown_from_peak_60d",
    "price_vs_ma20",
    "pre_trend_slope_norm",
    "pre_return_20d",
    "pre_volatility_20d",
)

ALL_FEATURE_NAMES = COARSE_FEATURE_NAMES + CONTEXT_FEATURE_NAMES


def pattern_feature_to_dict(row: PatternFeature) -> dict[str, float]:
    payload: dict[str, float] = {}
    coarse = [float(value) for value in list(row.coarse_vector_json or [])]
    for idx, name in enumerate(COARSE_FEATURE_NAMES):
        if idx < len(coarse):
            payload[name] = coarse[idx]
    for key, value in (row.context_feature_json or {}).items():
        if key in CONTEXT_FEATURE_NAMES:
            try:
                payload[key] = float(value)
            except (TypeError, ValueError):
                continue
    return payload
