from __future__ import annotations

from datetime import date
from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


class StubResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class StubHttpClient:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.calls: list[tuple[str, dict[str, object] | None]] = []

    def get(self, url: str, params: dict[str, object] | None = None, headers: dict[str, str] | None = None) -> StubResponse:
        self.calls.append((url, params))
        return StubResponse(self.payload)


def test_akshare_daily_price_feed_parses_eastmoney_kline_payload() -> None:
    from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed

    client = StubHttpClient(
        {
            "data": {
                "code": "600157",
                "name": "永泰能源",
                "klines": [
                    "2026-03-30,1.25,1.28,1.29,1.23,123456,987654321,4.80,2.40,0.03,1.20",
                    "2026-03-31,1.28,1.31,1.33,1.27,156789,1234567890,4.69,2.34,0.03,1.05",
                ],
            }
        }
    )

    rows = AkshareDailyPriceFeed(client=client).fetch_daily_prices(
        stock_code="600157",
        start=date(2025, 4, 1),
        end=date(2026, 3, 31),
    )

    assert len(rows) == 2
    assert rows[0]["stock_code"] == "600157"
    assert rows[0]["trade_date"] == date(2026, 3, 30)
    assert rows[0]["open_price"] == 1.25
    assert rows[0]["close_price"] == 1.28
    assert rows[0]["turnover_rate"] == 1.2
    assert rows[0]["data_source"] == "akshare"
    assert rows[1]["pre_close_price"] == 1.28
    assert client.calls[0][1]["secid"] == "1.600157"


def test_akshare_daily_price_feed_returns_metadata() -> None:
    from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed

    client = StubHttpClient({"data": {"code": "600157", "name": "永泰能源", "klines": []}})

    metadata = AkshareDailyPriceFeed(client=client).fetch_stock_metadata("600157")

    assert metadata["stock_code"] == "600157"
    assert metadata["stock_name"] == "永泰能源"
    assert metadata["market"] == "A"


def test_import_market_data_uses_real_feed_by_default() -> None:
    from swinginsight.jobs.import_market_data import build_daily_price_feed

    feed, source_name = build_daily_price_feed(demo=False)

    assert source_name == "akshare"
    assert feed.__class__.__name__ == "AkshareDailyPriceFeed"
