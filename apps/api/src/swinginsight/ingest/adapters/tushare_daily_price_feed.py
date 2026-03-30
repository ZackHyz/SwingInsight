from __future__ import annotations

from datetime import date


class TushareDailyPriceFeed:
    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None):
        raise NotImplementedError("Tushare daily price integration will be wired in a later task.")
