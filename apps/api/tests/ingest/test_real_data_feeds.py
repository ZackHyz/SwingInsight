from __future__ import annotations

from datetime import date
from pathlib import Path
import types
import sys

import pandas as pd
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
        self.pro_bar_calls: list[dict[str, object]] = []
        self.stock_basic_calls: list[dict[str, object]] = []

    def pro_bar(self, **kwargs: object) -> list[dict[str, object]]:
        self.pro_bar_calls.append(kwargs)
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
                "turnover_rate": 1.2,
                "adj_factor": 1.0,
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
                "turnover_rate": 1.1,
                "adj_factor": 1.0,
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


class EmptyTushareMetadataClient:
    def stock_basic(self, **kwargs: object) -> list[dict[str, object]]:
        return []


class FakeTushareModule:
    def __init__(self) -> None:
        self.token_values: list[str] = []
        self.pro_bar_calls: list[dict[str, object]] = []

    def set_token(self, token: str) -> None:
        self.token_values.append(token)

    def pro_bar(self, **kwargs: object) -> list[dict[str, object]]:
        self.pro_bar_calls.append(kwargs)
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
                "turnover_rate": 1.2,
                "adj_factor": 1.0,
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
                "turnover_rate": 1.1,
                "adj_factor": 1.0,
            },
        ]


class FakeMootdxClient:
    def __init__(self) -> None:
        self.bars_calls: list[dict[str, object]] = []

    def bars(self, **kwargs: object) -> pd.DataFrame:
        self.bars_calls.append(kwargs)
        return pd.DataFrame(
            [
                {
                    "open": 1.28,
                    "close": 1.31,
                    "high": 1.33,
                    "low": 1.27,
                    "vol": 156789,
                    "volume": 156789,
                    "amount": 1234567890,
                    "year": 2026,
                    "month": 3,
                    "day": 31,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-03-31 15:00:00",
                },
                {
                    "open": 1.25,
                    "close": 1.28,
                    "high": 1.29,
                    "low": 1.23,
                    "vol": 123456,
                    "volume": 123456,
                    "amount": 987654321,
                    "year": 2026,
                    "month": 3,
                    "day": 30,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-03-30 15:00:00",
                },
            ]
        )


class PagedMootdxClient:
    def __init__(self) -> None:
        self.bars_calls: list[dict[str, object]] = []

    def bars(self, **kwargs: object) -> pd.DataFrame:
        self.bars_calls.append(kwargs)
        start = int(kwargs["start"])
        if start == 0:
            rows = [
                {
                    "open": 1.34,
                    "close": 1.36,
                    "high": 1.37,
                    "low": 1.33,
                    "vol": 200000,
                    "volume": 200000,
                    "amount": 1230000000,
                    "year": 2026,
                    "month": 4,
                    "day": 3,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-04-03 15:00:00",
                },
                {
                    "open": 1.32,
                    "close": 1.34,
                    "high": 1.35,
                    "low": 1.31,
                    "vol": 190000,
                    "volume": 190000,
                    "amount": 1180000000,
                    "year": 2026,
                    "month": 4,
                    "day": 2,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-04-02 15:00:00",
                },
            ]
        elif start == 800:
            rows = [
                {
                    "open": 1.28,
                    "close": 1.31,
                    "high": 1.33,
                    "low": 1.27,
                    "vol": 156789,
                    "volume": 156789,
                    "amount": 987654321,
                    "year": 2026,
                    "month": 4,
                    "day": 1,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-04-01 15:00:00",
                },
                {
                    "open": 1.25,
                    "close": 1.28,
                    "high": 1.29,
                    "low": 1.23,
                    "vol": 123456,
                    "volume": 123456,
                    "amount": 876543210,
                    "year": 2026,
                    "month": 3,
                    "day": 31,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-03-31 15:00:00",
                },
            ]
        else:
            rows = []
        return pd.DataFrame(rows)


class LowLevelMootdxSecurityClient:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, str, int, int]] = []

    def get_security_bars(self, frequency: int, market: int, symbol: str, start: int, offset: int) -> pd.DataFrame:
        self.calls.append((frequency, market, symbol, start, offset))
        if symbol != "920019" or market != 2:
            return pd.DataFrame([])
        return pd.DataFrame(
            [
                {
                    "open": 2.31,
                    "close": 2.34,
                    "high": 2.36,
                    "low": 2.28,
                    "vol": 54321,
                    "amount": 123456789,
                    "year": 2026,
                    "month": 4,
                    "day": 1,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-04-01 15:00:00",
                },
                {
                    "open": 2.28,
                    "close": 2.31,
                    "high": 2.33,
                    "low": 2.25,
                    "vol": 43210,
                    "amount": 98765432,
                    "year": 2026,
                    "month": 3,
                    "day": 31,
                    "hour": 15,
                    "minute": 0,
                    "datetime": "2026-03-31 15:00:00",
                },
            ]
        )


class LowLevelMootdxQuoteClient:
    def __init__(self) -> None:
        self.client = LowLevelMootdxSecurityClient()


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


def test_mootdx_daily_price_feed_maps_bars_to_unified_rows() -> None:
    from swinginsight.ingest.adapters.mootdx_daily_price_feed import MootdxDailyPriceFeed

    fake_client = FakeMootdxClient()

    rows = MootdxDailyPriceFeed(client=fake_client).fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 30),
        end=date(2026, 3, 31),
    )

    assert len(rows) == 2
    assert rows[0]["stock_code"] == "600157"
    assert rows[0]["trade_date"] == date(2026, 3, 30)
    assert rows[0]["open_price"] == 1.25
    assert rows[0]["close_price"] == 1.28
    assert rows[0]["pre_close_price"] is None
    assert rows[0]["change_amount"] is None
    assert rows[0]["change_pct"] is None
    assert rows[0]["amplitude_pct"] is None
    assert rows[0]["turnover_rate"] is None
    assert rows[0]["adj_type"] == "raw"
    assert rows[0]["adj_factor"] is None
    assert rows[0]["is_trading_day"] is True
    assert rows[0]["data_source"] == "mootdx"
    assert fake_client.bars_calls[0] == {
        "symbol": "600157",
        "frequency": 9,
        "start": 0,
        "offset": 800,
    }


def test_mootdx_daily_price_feed_pages_until_it_reaches_requested_start_date() -> None:
    from swinginsight.ingest.adapters.mootdx_daily_price_feed import MootdxDailyPriceFeed

    fake_client = PagedMootdxClient()

    rows = MootdxDailyPriceFeed(client=fake_client).fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 31),
        end=date(2026, 4, 1),
    )

    assert len(rows) == 2
    assert rows[0]["trade_date"] == date(2026, 3, 31)
    assert rows[1]["trade_date"] == date(2026, 4, 1)
    assert len(fake_client.bars_calls) == 2
    assert fake_client.bars_calls[0]["start"] == 0
    assert fake_client.bars_calls[1]["start"] == 800


def test_mootdx_daily_price_feed_rejects_invalid_symbol() -> None:
    from swinginsight.ingest.adapters.mootdx_daily_price_feed import MootdxDailyPriceFeed

    fake_client = FakeMootdxClient()

    with pytest.raises(ValueError, match="6-digit stock code"):
        MootdxDailyPriceFeed(client=fake_client).fetch_daily_prices(
            stock_code="12345",
            start=date(2026, 3, 30),
            end=date(2026, 3, 31),
        )


def test_mootdx_daily_price_feed_uses_bj_market_id_for_920_symbols() -> None:
    from swinginsight.ingest.adapters.mootdx_daily_price_feed import MootdxDailyPriceFeed

    fake_client = LowLevelMootdxQuoteClient()

    rows = MootdxDailyPriceFeed(client=fake_client).fetch_daily_prices(
        stock_code="920019",
        start=date(2026, 3, 31),
        end=date(2026, 4, 1),
    )

    assert len(rows) == 2
    assert rows[0]["stock_code"] == "920019"
    assert rows[0]["trade_date"] == date(2026, 3, 31)
    assert rows[0]["data_source"] == "mootdx"
    assert fake_client.client.calls[0] == (9, 2, "920019", 0, 800)


def test_mootdx_daily_price_feed_resolves_runtime_client_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from swinginsight.ingest.adapters import mootdx_daily_price_feed as mootdx_feed

    factory_calls: list[tuple[str, dict[str, object]]] = []
    fake_client = PagedMootdxClient()

    def fake_factory(market: str = "std", **kwargs: object) -> PagedMootdxClient:
        factory_calls.append((market, kwargs))
        return fake_client

    monkeypatch.setattr(mootdx_feed.Quotes, "factory", staticmethod(fake_factory))

    rows = mootdx_feed.MootdxDailyPriceFeed().fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 31),
        end=date(2026, 4, 1),
    )

    assert len(rows) == 2
    assert len(factory_calls) == 1
    assert len(fake_client.bars_calls) == 2


def test_tushare_daily_price_feed_uses_module_level_qfq_contract(monkeypatch: pytest.MonkeyPatch) -> None:
    from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed

    fake_module = FakeTushareModule()
    fake_tushare = types.ModuleType("tushare")
    fake_tushare.set_token = fake_module.set_token
    fake_tushare.pro_bar = fake_module.pro_bar
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
    assert fake_module.token_values == ["token"]
    assert fake_module.pro_bar_calls[0]["ts_code"] == "600157.SH"
    assert fake_module.pro_bar_calls[0]["start_date"] == "20260330"
    assert fake_module.pro_bar_calls[0]["end_date"] == "20260331"
    assert fake_module.pro_bar_calls[0]["adj"] == "qfq"


def test_tushare_daily_price_feed_allows_injected_client_without_token() -> None:
    from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed

    fake_client = FakeTushareClient()

    rows = TushareDailyPriceFeed(client=fake_client).fetch_daily_prices(
        stock_code="600157",
        start=date(2026, 3, 30),
        end=date(2026, 3, 31),
    )

    assert rows[0]["stock_code"] == "600157"
    assert rows[0]["data_source"] == "tushare"
    assert fake_client.pro_bar_calls[0]["adj"] == "qfq"


def test_tushare_daily_price_feed_requires_token() -> None:
    from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed

    with pytest.raises(ValueError, match="Tushare token is required to fetch daily prices"):
        TushareDailyPriceFeed().fetch_daily_prices(
            stock_code="600157",
            start=date(2026, 3, 30),
            end=date(2026, 3, 31),
        )


def test_tushare_daily_price_feed_rejects_blank_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from swinginsight.ingest.adapters.tushare_daily_price_feed import TushareDailyPriceFeed

    fake_client = FakeTushareClient()
    fake_tushare = types.ModuleType("tushare")
    fake_tushare.pro_api = lambda token: fake_client
    monkeypatch.setitem(sys.modules, "tushare", fake_tushare)

    with pytest.raises(ValueError, match="Tushare token is required to fetch daily prices"):
        TushareDailyPriceFeed(token="   ").fetch_daily_prices(
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


def test_tushare_metadata_feed_rejects_blank_token(monkeypatch: pytest.MonkeyPatch) -> None:
    from swinginsight.ingest.adapters.tushare_metadata_feed import TushareMetadataFeed

    fake_client = FakeTushareClient()
    fake_tushare = types.ModuleType("tushare")
    fake_tushare.pro_api = lambda token: fake_client
    monkeypatch.setitem(sys.modules, "tushare", fake_tushare)

    with pytest.raises(ValueError, match="Tushare token is required to fetch stock metadata"):
        TushareMetadataFeed(token="   ").fetch_stock_metadata("600157")


def test_tushare_metadata_feed_treats_empty_response_as_miss() -> None:
    from swinginsight.ingest.adapters.tushare_metadata_feed import TushareMetadataFeed

    with pytest.raises(ValueError, match="Tushare stock metadata not found for 600157"):
        TushareMetadataFeed(client=EmptyTushareMetadataClient(), token="token").fetch_stock_metadata("600157")


def test_import_market_data_uses_real_feed_by_default() -> None:
    from swinginsight.jobs.import_market_data import build_daily_price_feed
    from swinginsight.settings import Settings

    feed, source_name = build_daily_price_feed(demo=False, settings=Settings.model_validate({}))

    assert source_name == "priority"
    assert feed.provider_names == ["akshare", "tushare", "mootdx"]
