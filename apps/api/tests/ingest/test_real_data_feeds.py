from __future__ import annotations

from datetime import date
from pathlib import Path
import types
import sys

import pytest


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


class FakeTushareClient:
    def __init__(self) -> None:
        self.daily_calls: list[dict[str, object]] = []
        self.stock_basic_calls: list[dict[str, object]] = []

    def daily(self, **kwargs: object) -> list[dict[str, object]]:
        self.daily_calls.append(kwargs)
        return [
            {
                "ts_code": "600157.SH",
                "trade_date": "20260330",
                "open": 1.25,
                "close": 1.28,
                "high": 1.29,
                "low": 1.23,
                "vol": 123456,
                "amount": 987654321,
                "change": 0.03,
                "pct_chg": 2.4,
                "pre_close": 1.25,
            },
            {
                "ts_code": "600157.SH",
                "trade_date": "20260331",
                "open": 1.28,
                "close": 1.31,
                "high": 1.33,
                "low": 1.27,
                "vol": 156789,
                "amount": 1234567890,
                "change": 0.03,
                "pct_chg": 1.05,
                "pre_close": 1.28,
            },
        ]

    def stock_basic(self, **kwargs: object) -> list[dict[str, object]]:
        self.stock_basic_calls.append(kwargs)
        return [
            {
                "ts_code": "600157.SH",
                "name": "永泰能源",
                "industry": None,
                "market": "A",
            }
        ]


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


def test_tushare_daily_price_feed_uses_pro_api_daily_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed

    fake_client = FakeTushareClient()
    fake_tushare = types.ModuleType("tushare")
    fake_tushare.pro_api = lambda token: fake_client
    monkeypatch.setitem(sys.modules, "tushare", fake_tushare)

    rows = TushareDailyPriceFeed(token="token").fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 30),
        end=date(2026, 3, 31),
    )

    assert rows[0]["stock_code"] == "600157"
    assert rows[0]["trade_date"] == date(2026, 3, 30)
    assert rows[0]["close_price"] == 1.28
    assert rows[0]["data_source"] == "tushare"
    assert fake_client.daily_calls[0]["ts_code"] == "600157.SH"


def test_tushare_daily_price_feed_requires_token() -> None:
    from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed

    with pytest.raises(ValueError, match="Tushare token is required to fetch daily prices"):
        TushareDailyPriceFeed().fetch_daily_prices(
            stock_code="600157",
            start=date(2026, 3, 30),
            end=date(2026, 3, 31),
        )


def test_tushare_metadata_feed_maps_stock_basic_row() -> None:
    from swinginsight.ingest.adapters.tushare_metadata_feed import TushareMetadataFeed

    fake_client = FakeTushareClient()

    metadata = TushareMetadataFeed(client=fake_client, token="token").fetch_stock_metadata("600157")

    assert metadata["stock_code"] == "600157"
    assert metadata["stock_name"] == "永泰能源"
    assert metadata["market"] == "A"
    assert metadata["industry"] is None
    assert metadata["concept_tags"] == []
    assert fake_client.stock_basic_calls[0]["ts_code"] == "600157.SH"


def test_tushare_metadata_feed_requires_token() -> None:
    from swinginsight.ingest.adapters.tushare_metadata_feed import TushareMetadataFeed

    with pytest.raises(ValueError, match="Tushare token is required to fetch stock metadata"):
        TushareMetadataFeed().fetch_stock_metadata("600157")


def test_import_market_data_uses_real_feed_by_default() -> None:
    from swinginsight.jobs.import_market_data import build_daily_price_feed

    feed, source_name = build_daily_price_feed(demo=False)

    assert source_name == "akshare"
    assert feed.__class__.__name__ == "AkshareDailyPriceFeed"
