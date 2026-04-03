from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def make_rows(count: int) -> list[object]:
    from swinginsight.db.models.market_data import DailyPrice

    rows: list[DailyPrice] = []
    close_price = 10.0
    for index in range(count):
        close_price += 0.05 if index % 3 else 0.12
        rows.append(
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 1) + timedelta(days=index),
                open_price=close_price - 0.08,
                high_price=close_price + 0.15,
                low_price=close_price - 0.18,
                close_price=close_price,
                volume=1_000_000 + index * 10_000,
                turnover_rate=2.0 + index * 0.03,
                adj_type="qfq",
                data_source="test",
            )
        )
    return rows


def test_build_pattern_features_outputs_expected_component_shapes() -> None:
    from swinginsight.domain.prediction.pattern_features import build_pattern_features

    history_rows = make_rows(80)
    features = build_pattern_features(window_rows=history_rows[-7:], history_rows=history_rows)

    assert features is not None
    assert len(features["price_seq"]) == 7
    assert len(features["return_seq"]) == 7
    assert len(features["candle_feat"]) == 35
    assert len(features["volume_seq"]) == 7
    assert len(features["turnover_seq"]) == 7
    assert len(features["trend_context"]) >= 8
    assert len(features["vola_context"]) >= 5
    assert len(features["coarse_vector"]) > 0


def test_build_pattern_features_skips_windows_without_context() -> None:
    from swinginsight.domain.prediction.pattern_features import build_pattern_features

    short_history = make_rows(20)
    assert build_pattern_features(window_rows=short_history[-7:], history_rows=short_history) is None
