from __future__ import annotations

from datetime import date


class DemoDailyPriceFeed:
    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        return [
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 2),
                "open_price": 10,
                "high_price": 11,
                "low_price": 9,
                "close_price": 10.5,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 3),
                "open_price": 10.5,
                "high_price": 11.5,
                "low_price": 10,
                "close_price": 11,
                "adj_type": "qfq",
                "data_source": "demo",
            },
        ]
