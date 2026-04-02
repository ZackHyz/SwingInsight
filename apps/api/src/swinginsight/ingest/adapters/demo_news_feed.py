from __future__ import annotations

from datetime import date, datetime


class DemoNewsFeed:
    def fetch_news(self, stock_code: str, start: date | None, end: date | None):
        return [
            {
                "news_uid": f"{stock_code}-news-1",
                "stock_code": stock_code,
                "title": "2025年业绩预告同比扭亏",
                "summary": "演示公告新闻",
                "content": "演示公告新闻正文",
                "publish_time": datetime(2024, 1, 2, 9, 0, 0),
                "news_date": date(2024, 1, 2),
                "source_name": "demo",
                "source_type": "announcement",
                "url": f"https://demo.local/{stock_code}/news-1",
                "raw_json": {"id": 1, "stock_code": stock_code},
                "data_source": "demo",
            },
            {
                "news_uid": f"{stock_code}-news-2",
                "stock_code": stock_code,
                "title": "签署重大订单协议",
                "summary": "演示媒体新闻",
                "content": "演示媒体新闻正文",
                "publish_time": datetime(2024, 1, 3, 10, 0, 0),
                "news_date": date(2024, 1, 3),
                "source_name": "demo",
                "source_type": "media_news",
                "url": f"https://demo.local/{stock_code}/news-2",
                "raw_json": {"id": 2, "stock_code": stock_code},
                "data_source": "demo",
            },
        ]
