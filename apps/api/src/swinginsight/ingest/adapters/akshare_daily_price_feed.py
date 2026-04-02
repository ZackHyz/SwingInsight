from __future__ import annotations

from datetime import date
from typing import Any

import httpx


class AkshareDailyPriceFeed:
    base_url = "https://push2his.eastmoney.com/api/qt/stock/kline/get"

    def __init__(self, client: httpx.Client | Any | None = None) -> None:
        self.client = client

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, Any]]:
        payload = self._fetch_payload(stock_code=stock_code, start=start, end=end)
        data = payload.get("data") or {}
        klines = data.get("klines") or []
        rows: list[dict[str, Any]] = []
        previous_close: float | None = None

        for raw_line in klines:
            parts = str(raw_line).split(",")
            if len(parts) < 11:
                continue
            close_price = float(parts[2])
            rows.append(
                {
                    "stock_code": stock_code,
                    "trade_date": date.fromisoformat(parts[0]),
                    "open_price": float(parts[1]),
                    "close_price": close_price,
                    "high_price": float(parts[3]),
                    "low_price": float(parts[4]),
                    "volume": int(float(parts[5])),
                    "amount": float(parts[6]),
                    "amplitude_pct": float(parts[7]),
                    "change_pct": float(parts[8]),
                    "change_amount": float(parts[9]),
                    "turnover_rate": float(parts[10]),
                    "pre_close_price": previous_close,
                    "adj_type": "qfq",
                    "is_trading_day": True,
                    "data_source": "akshare",
                }
            )
            previous_close = close_price
        return rows

    def fetch_stock_metadata(self, stock_code: str) -> dict[str, Any]:
        payload = self._fetch_payload(stock_code=stock_code, start=None, end=None)
        data = payload.get("data") or {}
        return {
            "stock_code": stock_code,
            "stock_name": str(data.get("name") or stock_code),
            "market": "A",
            "industry": None,
            "concept_tags": [],
        }

    def _fetch_payload(self, stock_code: str, start: date | None, end: date | None) -> dict[str, Any]:
        params = {
            "secid": self._to_secid(stock_code),
            "fields1": "f1,f2,f3,f4,f5,f6",
            "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
            "klt": "101",
            "fqt": "1",
            "beg": (start or date(1990, 1, 1)).strftime("%Y%m%d"),
            "end": (end or date.today()).strftime("%Y%m%d"),
        }
        headers = {
            "Referer": "https://quote.eastmoney.com/",
            "User-Agent": "Mozilla/5.0",
        }
        if self.client is None:
            with httpx.Client(timeout=15.0) as client:
                response = client.get(self.base_url, params=params, headers=headers)
        else:
            response = self.client.get(self.base_url, params=params, headers=headers)
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, dict):
            raise ValueError("Unexpected Eastmoney kline response")
        return payload

    def _to_secid(self, stock_code: str) -> str:
        if stock_code.startswith(("5", "6", "9")):
            return f"1.{stock_code}"
        return f"0.{stock_code}"
