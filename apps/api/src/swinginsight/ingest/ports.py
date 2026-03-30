from __future__ import annotations

from datetime import date
from typing import Any, Protocol


class DailyPriceFeed(Protocol):
    def fetch_daily_prices(
        self,
        stock_code: str,
        start: date | None,
        end: date | None,
    ) -> list[dict[str, Any]]: ...


class TradeRecordFeed(Protocol):
    def fetch_trade_records(
        self,
        stock_code: str,
        start: date | None,
        end: date | None,
    ) -> list[dict[str, Any]]: ...


class NewsFeed(Protocol):
    def fetch_news(
        self,
        stock_code: str,
        start: date | None,
        end: date | None,
    ) -> list[dict[str, Any]]: ...


class MetadataFeed(Protocol):
    def fetch_stock_metadata(self, stock_code: str) -> dict[str, Any]: ...
