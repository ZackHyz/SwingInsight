from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_price_similarity_prefers_closer_path() -> None:
    from swinginsight.domain.prediction.pattern_similarity import sim_price

    current = [1.0, 0.99, 0.97, 0.96, 0.98, 1.01, 1.03]
    close_match = [1.0, 0.995, 0.972, 0.961, 0.981, 1.008, 1.028]
    noisy_match = [1.0, 1.03, 0.95, 1.06, 0.94, 1.08, 0.9]

    assert sim_price(current, close_match) > sim_price(current, noisy_match)


def test_candle_similarity_penalizes_reversed_bull_bear_order() -> None:
    from swinginsight.domain.prediction.pattern_similarity import sim_candle

    current = {
        "candle_feat": [
            0.5, 0.1, 0.4, 0.8, 1.0,
            0.4, 0.2, 0.4, 0.7, 1.0,
            0.6, 0.1, 0.3, 0.9, 1.0,
            0.3, 0.2, 0.5, 0.4, 0.0,
            0.2, 0.3, 0.5, 0.3, 0.0,
            0.5, 0.2, 0.3, 0.8, 1.0,
            0.4, 0.2, 0.4, 0.7, 1.0,
        ],
        "bull_flags": [1, 1, 1, 0, 0, 1, 1],
        "highest_day_pos": 5,
        "lowest_day_pos": 3,
    }
    aligned = {
        "candle_feat": current["candle_feat"],
        "bull_flags": [1, 1, 1, 0, 0, 1, 1],
        "highest_day_pos": 5,
        "lowest_day_pos": 3,
    }
    reversed_order = {
        "candle_feat": current["candle_feat"],
        "bull_flags": [0, 0, 1, 1, 1, 0, 0],
        "highest_day_pos": 1,
        "lowest_day_pos": 6,
    }

    assert sim_candle(current, aligned) > sim_candle(current, reversed_order)


def test_total_similarity_uses_all_components() -> None:
    from swinginsight.domain.prediction.pattern_similarity import calc_pattern_similarity

    query_features = {
        "price_seq": [1.0, 0.99, 0.97, 0.96, 0.98, 1.01, 1.03],
        "candle_feat": [0.5] * 35,
        "bull_flags": [1, 1, 0, 0, 1, 1, 1],
        "highest_day_pos": 6,
        "lowest_day_pos": 3,
        "volume_seq": [0.9, 1.0, 1.2, 0.8, 1.1, 1.3, 1.2],
        "turnover_seq": [0.8, 0.9, 1.1, 0.9, 1.0, 1.2, 1.1],
        "trend_context": [1.0, 0.98, 0.95, 0.92, 0.02, 0.03, 0.04, 0.0, 1.0, 0.0],
        "vola_context": [0.04, 0.05, 0.09, 0.03, 0.06],
    }
    sample_features = {
        "price_seq": [1.0, 0.992, 0.971, 0.958, 0.979, 1.006, 1.027],
        "candle_feat": [0.52] * 35,
        "bull_flags": [1, 1, 0, 0, 1, 1, 1],
        "highest_day_pos": 6,
        "lowest_day_pos": 3,
        "volume_seq": [0.92, 1.02, 1.18, 0.82, 1.08, 1.28, 1.16],
        "turnover_seq": [0.82, 0.93, 1.06, 0.88, 1.02, 1.16, 1.09],
        "trend_context": [1.01, 0.99, 0.96, 0.93, 0.02, 0.03, 0.04, 0.0, 1.0, 0.0],
        "vola_context": [0.039, 0.049, 0.088, 0.031, 0.059],
    }

    result = calc_pattern_similarity(query_features, sample_features)

    assert set(result) >= {
        "total_similarity",
        "sim_price",
        "sim_candle",
        "sim_volume",
        "sim_turnover",
        "sim_trend",
        "sim_vola",
    }
    assert 0.0 <= result["total_similarity"] <= 1.0
