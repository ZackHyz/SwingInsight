from __future__ import annotations

from datetime import date
from typing import Any

import pandas as pd

from mootdx.quotes import Quotes
from mootdx.utils import get_stock_market


class MootdxDailyPriceFeed:
    def __init__(self, client: Any | None = None) -> None:
        self.client = client

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, Any]]:
        symbol = self._normalize_stock_code(stock_code)
        self._infer_market(symbol)
        rows = self._rows_from_response(
            self._get_client().bars(
                symbol=symbol,
                frequency=9,
                start=0,
                offset=800,
            )
        )
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
        if normalized.startswith(("sh", "sz", "SH", "SZ")):
            normalized = normalized[2:]
        return normalized

    def _infer_market(self, stock_code: str) -> str:
        market = get_stock_market(stock_code, string=True)
        if market not in {"sh", "sz"}:
            raise ValueError(f"Mootdx daily prices only support Shanghai/Shenzhen stock codes: {stock_code}")
        return market

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
