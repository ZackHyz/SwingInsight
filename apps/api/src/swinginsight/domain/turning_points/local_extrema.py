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
        previous_close = float(price_series[index - 1]["close_price"])
        current_close = float(price_series[index]["close_price"])
        next_close = float(price_series[index + 1]["close_price"])
        trade_date = price_series[index]["trade_date"]
        if not isinstance(trade_date, date):
            raise TypeError("trade_date must be a date")

        if current_close <= previous_close and current_close <= next_close:
            points.append(LocalExtremaPoint(point_date=trade_date, point_type="trough", point_price=current_close))
        elif current_close >= previous_close and current_close >= next_close:
            points.append(LocalExtremaPoint(point_date=trade_date, point_type="peak", point_price=current_close))

    return points
