from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from swinginsight.domain.turning_points.local_extrema import detect_local_extrema


@dataclass(slots=True, frozen=True)
class DetectedTurningPoint:
    point_date: date
    point_type: str
    point_price: float
    confirm_date: date | None = None


class ZigZagDetector:
    def __init__(self, reversal_pct: float) -> None:
        if reversal_pct <= 0:
            raise ValueError("reversal_pct must be positive")
        self.reversal_pct = reversal_pct

    def detect(self, price_series: list[dict[str, object]]) -> list[DetectedTurningPoint]:
        extrema = detect_local_extrema(price_series)
        if not extrema:
            return []

        confirmed: list[DetectedTurningPoint] = []
        for candidate in extrema:
            if not confirmed:
                confirmed.append(
                    DetectedTurningPoint(
                        point_date=candidate.point_date,
                        point_type=candidate.point_type,
                        point_price=candidate.point_price,
                        confirm_date=self._find_confirm_date(
                            price_series=price_series,
                            point_date=candidate.point_date,
                            point_price=candidate.point_price,
                            point_type=candidate.point_type,
                        ),
                    )
                )
                continue

            previous = confirmed[-1]
            if previous.point_type == candidate.point_type:
                if candidate.point_type == "peak" and candidate.point_price >= previous.point_price:
                    confirmed[-1] = DetectedTurningPoint(
                        point_date=candidate.point_date,
                        point_type=candidate.point_type,
                        point_price=candidate.point_price,
                        confirm_date=self._find_confirm_date(
                            price_series=price_series,
                            point_date=candidate.point_date,
                            point_price=candidate.point_price,
                            point_type=candidate.point_type,
                        ),
                    )
                elif candidate.point_type == "trough" and candidate.point_price <= previous.point_price:
                    confirmed[-1] = DetectedTurningPoint(
                        point_date=candidate.point_date,
                        point_type=candidate.point_type,
                        point_price=candidate.point_price,
                        confirm_date=self._find_confirm_date(
                            price_series=price_series,
                            point_date=candidate.point_date,
                            point_price=candidate.point_price,
                            point_type=candidate.point_type,
                        ),
                    )
                continue

            reversal = abs(candidate.point_price - previous.point_price) / previous.point_price
            if reversal >= self.reversal_pct:
                confirmed.append(
                    DetectedTurningPoint(
                        point_date=candidate.point_date,
                        point_type=candidate.point_type,
                        point_price=candidate.point_price,
                        confirm_date=self._find_confirm_date(
                            price_series=price_series,
                            point_date=candidate.point_date,
                            point_price=candidate.point_price,
                            point_type=candidate.point_type,
                        ),
                    )
                )

        final_point = self._build_terminal_point(price_series=price_series, confirmed=confirmed)
        if final_point is not None:
            confirmed.append(final_point)

        return confirmed

    def _find_confirm_date(
        self,
        *,
        price_series: list[dict[str, object]],
        point_date: date,
        point_price: float,
        point_type: str,
    ) -> date | None:
        threshold = point_price * (1 + self.reversal_pct if point_type == "trough" else 1 - self.reversal_pct)
        seen_point = False
        for row in price_series:
            trade_date = row["trade_date"]
            if not isinstance(trade_date, date):
                raise TypeError("trade_date must be a date")
            if trade_date == point_date:
                seen_point = True
                continue
            if not seen_point:
                continue

            close_price = float(row["close_price"])
            if point_type == "trough" and close_price >= threshold:
                return trade_date
            if point_type == "peak" and close_price <= threshold:
                return trade_date
        return None

    def _build_terminal_point(
        self, *, price_series: list[dict[str, object]], confirmed: list[DetectedTurningPoint]
    ) -> DetectedTurningPoint | None:
        if not confirmed or not price_series:
            return None

        last_row = price_series[-1]
        trade_date = last_row["trade_date"]
        if not isinstance(trade_date, date):
            raise TypeError("trade_date must be a date")
        close_price = float(last_row["close_price"])
        previous = confirmed[-1]
        if previous.point_date == trade_date:
            return None

        point_type = "peak" if previous.point_type == "trough" else "trough"
        reversal = abs(close_price - previous.point_price) / previous.point_price
        if reversal < self.reversal_pct:
            return None

        return DetectedTurningPoint(
            point_date=trade_date,
            point_type=point_type,
            point_price=close_price,
            confirm_date=trade_date,
        )
