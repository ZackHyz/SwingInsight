from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from mootdx.quotes import Quotes


class MootdxDailyPriceFeed:
    page_size = 800

    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, Any]]:
        symbol = self._normalize_stock_code(stock_code)
        market_id = self._market_id_for_symbol(symbol)
        client = self._get_client()
        rows = self._fetch_rows(client=client, symbol=symbol, market_id=market_id, start=start, end=end)
        payloads = [self._map_row(stock_code=symbol, row=row) for row in rows]
        if start is not None or end is not None:
            payloads = [
                payload
                for payload in payloads
                if (start is None or payload["trade_date"] >= start)
                and (end is None or payload["trade_date"] <= end)
            ]
        return sorted(payloads, key=lambda payload: payload["trade_date"])

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        return Quotes.factory(market="std")

    def _normalize_stock_code(self, stock_code: str) -> str:
        normalized = stock_code.strip()
        if "." in normalized:
            normalized = normalized.split(".", 1)[0]
        if normalized.startswith(("sh", "sz", "bj", "SH", "SZ", "BJ")):
            normalized = normalized[2:]
        if len(normalized) != 6 or not normalized.isdigit():
            raise ValueError("Mootdx daily prices require a 6-digit stock code")
        return normalized

    def _market_id_for_symbol(self, stock_code: str) -> int:
        if stock_code.startswith(("4", "8", "92")):
            return 2
        if stock_code.startswith(("5", "6", "7", "9")):
            return 1
        if stock_code.startswith(("0", "1", "2", "3")):
            return 0
        raise ValueError(f"Mootdx daily prices only support Shanghai/Shenzhen/BJ stock codes: {stock_code}")

    def _fetch_rows(
        self,
        client: Any,
        symbol: str,
        market_id: int,
        start: date | None,
        end: date | None,
    ) -> list[dict[str, Any]]:
        target_date = start or end
        rows: list[dict[str, Any]] = []
        page_start = 0

        while True:
            page_rows = self._fetch_page_rows(client=client, symbol=symbol, market_id=market_id, start=page_start)
            if not page_rows:
                break

            rows.extend(page_rows)
            if target_date is None:
                break

            oldest_trade_date = min(self._parse_trade_date(row) for row in page_rows)
            if oldest_trade_date <= target_date:
                break

            page_start += self.page_size

        return rows

    def _fetch_page_rows(self, client: Any, symbol: str, market_id: int, start: int) -> list[dict[str, Any]]:
        security_client = getattr(client, "client", None)
        if security_client is not None and hasattr(security_client, "get_security_bars"):
            response = security_client.get_security_bars(9, market_id, symbol, start, self.page_size)
            return self._rows_from_response(response)

        bars = getattr(client, "bars", None)
        if callable(bars):
            response = bars(
                symbol=symbol,
                frequency=9,
                start=start,
                offset=self.page_size,
            )
            return self._rows_from_response(response)

        raise AttributeError("Mootdx client does not expose bars() or client.get_security_bars()")

    def _rows_from_response(self, response: Any) -> list[dict[str, Any]]:
        if response is None:
            return []
        if isinstance(response, pd.DataFrame):
            return [dict(row) for row in response.to_dict(orient="records")]
        if isinstance(response, list):
            return [dict(row) for row in response]
        if isinstance(response, dict):
            return [dict(response)]
        to_dict = getattr(response, "to_dict", None)
        if callable(to_dict):
            try:
                records = to_dict("records")
            except TypeError:
                records = to_dict(orient="records")
            if isinstance(records, list):
                return [dict(row) for row in records]
        return [dict(row) for row in response]

    def _map_row(self, stock_code: str, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "stock_code": stock_code,
            "trade_date": self._parse_trade_date(row),
            "open_price": self._to_float(row.get("open")),
            "high_price": self._to_float(row.get("high")),
            "low_price": self._to_float(row.get("low")),
            "close_price": self._to_float(row.get("close")),
            "pre_close_price": None,
            "change_amount": None,
            "change_pct": None,
            "volume": self._to_int(row.get("volume") if row.get("volume") is not None else row.get("vol")),
            "amount": self._to_float(row.get("amount")),
            "amplitude_pct": None,
            "turnover_rate": None,
            "adj_type": "raw",
            "adj_factor": None,
            "is_trading_day": True,
            "data_source": "mootdx",
        }

    def _parse_trade_date(self, row: dict[str, Any]) -> date:
        raw_datetime = row.get("datetime")
        if raw_datetime is not None and not pd.isna(raw_datetime):
            trade_datetime = pd.to_datetime(raw_datetime, errors="coerce")
            if not pd.isna(trade_datetime):
                return trade_datetime.date()

        year = row.get("year")
        month = row.get("month")
        day = row.get("day")
        if year is not None and month is not None and day is not None:
            return date(int(year), int(month), int(day))
        raise ValueError("Mootdx bar row is missing a trade date")

    def _to_float(self, value: Any) -> float | None:
        if value is None or pd.isna(value):
            return None
        return float(value)

    def _to_int(self, value: Any) -> int | None:
        if value is None or pd.isna(value):
            return None
        return int(float(value))
