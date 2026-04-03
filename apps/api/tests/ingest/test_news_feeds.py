from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


class FakeDataFrame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def to_dict(self, orient: str) -> list[dict[str, object]]:
        assert orient == "records"
        return list(self._rows)


def test_eastmoney_news_feed_maps_rows_and_filters_by_date(monkeypatch) -> None:
    from swinginsight.ingest.adapters import eastmoney_news_feed as eastmoney_module

    def fake_stock_news_em(symbol: str):
        assert symbol == "600010"
        return FakeDataFrame(
            [
                {
                    "关键词": symbol,
                    "新闻标题": "区间内新闻",
                    "新闻内容": "正文 A",
                    "发布时间": "2026-03-27 16:50:51",
                    "文章来源": "每日经济新闻",
                    "新闻链接": "https://example.com/eastmoney/in-range",
                },
                {
                    "关键词": symbol,
                    "新闻标题": "区间外新闻",
                    "新闻内容": "正文 B",
                    "发布时间": "2026-02-27 16:50:51",
                    "文章来源": "证券时报网",
                    "新闻链接": "https://example.com/eastmoney/out-of-range",
                },
            ]
        )

    monkeypatch.setattr(eastmoney_module, "ak", SimpleNamespace(stock_news_em=fake_stock_news_em))

    rows = eastmoney_module.EastmoneyNewsFeed().fetch_news(
        stock_code="600010",
        start=date(2026, 3, 1),
        end=date(2026, 3, 31),
    )

    assert len(rows) == 1
    assert rows[0] == {
        "news_uid": "eastmoney:600010:https://example.com/eastmoney/in-range",
        "stock_code": "600010",
        "title": "区间内新闻",
        "summary": "正文 A",
        "content": "正文 A",
        "publish_time": datetime(2026, 3, 27, 16, 50, 51),
        "news_date": date(2026, 3, 27),
        "source_name": "每日经济新闻",
        "source_type": "media_news",
        "url": "https://example.com/eastmoney/in-range",
        "raw_json": {
            "关键词": "600010",
            "新闻标题": "区间内新闻",
            "新闻内容": "正文 A",
            "发布时间": "2026-03-27 16:50:51",
            "文章来源": "每日经济新闻",
            "新闻链接": "https://example.com/eastmoney/in-range",
        },
        "data_source": "eastmoney",
    }


def test_cninfo_news_feed_maps_rows_and_formats_date_window(monkeypatch) -> None:
    from swinginsight.ingest.adapters import cninfo_news_feed as cninfo_module

    calls: list[tuple[str, str, str]] = []

    def fake_disclosure(symbol: str, market: str, keyword: str, category: str, start_date: str, end_date: str):
        calls.append((symbol, start_date, end_date))
        return FakeDataFrame(
            [
                {
                    "代码": symbol,
                    "简称": "包钢股份",
                    "公告标题": "包钢股份第七届董事会第四十三次会议决议公告",
                    "公告时间": "2026-03-21",
                    "公告链接": "http://www.cninfo.com.cn/new/disclosure/detail?stockCode=600010&announcementId=1225020786&orgId=gssh0600010&announcementTime=2026-03-21",
                }
            ]
        )

    monkeypatch.setattr(
        cninfo_module,
        "ak",
        SimpleNamespace(stock_zh_a_disclosure_report_cninfo=fake_disclosure),
    )

    rows = cninfo_module.CninfoNewsFeed().fetch_news(
        stock_code="600010",
        start=date(2026, 3, 1),
        end=date(2026, 4, 2),
    )

    assert calls == [("600010", "20260301", "20260402")]
    assert rows == [
        {
            "news_uid": "cninfo:600010:1225020786",
            "stock_code": "600010",
            "title": "包钢股份第七届董事会第四十三次会议决议公告",
            "summary": None,
            "content": None,
            "publish_time": datetime(2026, 3, 21, 0, 0, 0),
            "news_date": date(2026, 3, 21),
            "source_name": "cninfo",
            "source_type": "announcement",
            "url": "http://www.cninfo.com.cn/new/disclosure/detail?stockCode=600010&announcementId=1225020786&orgId=gssh0600010&announcementTime=2026-03-21",
            "raw_json": {
                "代码": "600010",
                "简称": "包钢股份",
                "公告标题": "包钢股份第七届董事会第四十三次会议决议公告",
                "公告时间": "2026-03-21",
                "公告链接": "http://www.cninfo.com.cn/new/disclosure/detail?stockCode=600010&announcementId=1225020786&orgId=gssh0600010&announcementTime=2026-03-21",
            },
            "data_source": "cninfo",
        }
    ]
