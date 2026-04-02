from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(slots=True, frozen=True)
class LocalExtremaPoint:
    point_date: date
    point_type: str
    point_price: float


def detect_local_extrema(price_series: list[dict[str, object]]) -> list[LocalExtremaPoint]:
    if len(price_series) < 3:
        return []

    points: list[LocalExtremaPoint] = []
    for index in range(1, len(price_series) - 1):
        previous_low = _price_value(price_series[index - 1], "low_price")
        current_low = _price_value(price_series[index], "low_price")
        next_low = _price_value(price_series[index + 1], "low_price")
        previous_high = _price_value(price_series[index - 1], "high_price")
        current_high = _price_value(price_series[index], "high_price")
        next_high = _price_value(price_series[index + 1], "high_price")
        trade_date = price_series[index]["trade_date"]
        if not isinstance(trade_date, date):
            raise TypeError("trade_date must be a date")

        if current_low <= previous_low and current_low <= next_low:
            points.append(LocalExtremaPoint(point_date=trade_date, point_type="trough", point_price=current_low))
        elif current_high >= previous_high and current_high >= next_high:
            points.append(LocalExtremaPoint(point_date=trade_date, point_type="peak", point_price=current_high))

    return points


def _price_value(row: dict[str, object], field_name: str) -> float:
    raw_value = row.get(field_name)
    if raw_value is None:
        raw_value = row["close_price"]
    return float(raw_value)
