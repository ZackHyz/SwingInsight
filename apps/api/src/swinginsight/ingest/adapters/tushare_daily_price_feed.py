from __future__ import annotations

from datetime import date
from typing import Any


class TushareDailyPriceFeed:
    def __init__(self, client: Any | None = None, token: str | None = None) -> None:
        self.client = client
        self.token = token.strip() if token else None

    def fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, Any]]:
        client = self._get_client()
        ts_code = self._to_ts_code(stock_code)
        rows = self._rows_from_response(
            client.pro_bar(
                ts_code=ts_code,
                start_date=start.strftime("%Y%m%d") if start else None,
                end_date=end.strftime("%Y%m%d") if end else None,
                adj="qfq",
                asset="E",
            )
        )
        payloads = [self._map_row(stock_code=stock_code, row=row) for row in rows]
        return sorted(payloads, key=lambda payload: payload["trade_date"])

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.token:
            raise ValueError("Tushare token is required to fetch daily prices")
        import tushare as ts

        return ts.pro_api(self.token)

    def _rows_from_response(self, response: Any) -> list[dict[str, Any]]:
        if response is None:
            return []
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
            "trade_date": self._parse_trade_date(row["trade_date"]),
            "open_price": self._to_float(row.get("open")),
            "high_price": self._to_float(row.get("high")),
            "low_price": self._to_float(row.get("low")),
            "close_price": self._to_float(row.get("close")),
            "pre_close_price": self._to_float(row.get("pre_close")),
            "change_amount": self._to_float(row.get("change")),
            "change_pct": self._to_float(row.get("pct_chg")),
            "volume": self._to_int(row.get("vol")),
            "amount": self._to_float(row.get("amount")),
            "amplitude_pct": self._to_float(row.get("amp")),
            "turnover_rate": self._to_float(row.get("turnover_rate")),
            "adj_type": "qfq",
            "adj_factor": self._to_float(row.get("adj_factor")),
            "is_trading_day": True,
            "data_source": "tushare",
        }

    def _parse_trade_date(self, value: Any) -> date:
        text = str(value)
        if len(text) == 8 and text.isdigit():
            return date(int(text[0:4]), int(text[4:6]), int(text[6:8]))
        return date.fromisoformat(text)

    def _to_float(self, value: Any) -> float | None:
        if value is None or value == "":
            return None
        return float(value)

    def _to_int(self, value: Any) -> int | None:
        if value is None or value == "":
            return None
        return int(float(value))

    def _to_ts_code(self, stock_code: str) -> str:
        normalized = stock_code.strip()
        if "." in normalized:
            return normalized.upper()
        if normalized.startswith(("5", "6", "9")):
            return f"{normalized}.SH"
        return f"{normalized}.SZ"
