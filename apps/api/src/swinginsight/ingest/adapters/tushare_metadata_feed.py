from __future__ import annotations

from typing import Any


class TushareMetadataFeed:
    def __init__(self, client: Any | None = None, token: str | None = None) -> None:
        self.client = client
        self.token = token.strip() if token else None

    def fetch_stock_metadata(self, stock_code: str) -> dict[str, Any]:
        client = self._get_client()
        ts_code = self._to_ts_code(stock_code)
        rows = self._rows_from_response(
            client.stock_basic(
                exchange="",
                list_status="L",
                ts_code=ts_code,
                fields="ts_code,symbol,name,area,industry,market,list_date",
            )
        )
        row = rows[0] if rows else {}
        return {
            "stock_code": stock_code,
            "stock_name": str(row.get("name") or stock_code),
            "market": str(row.get("market") or "A"),
            "industry": row.get("industry"),
            "concept_tags": [],
        }

    def _get_client(self) -> Any:
        if self.client is not None:
            return self.client
        if not self.token:
            raise ValueError("Tushare token is required to fetch stock metadata")
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

    def _to_ts_code(self, stock_code: str) -> str:
        normalized = stock_code.strip()
        if "." in normalized:
            return normalized.upper()
        if normalized.startswith(("5", "6", "9")):
            return f"{normalized}.SH"
        return f"{normalized}.SZ"
