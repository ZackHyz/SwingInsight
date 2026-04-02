from __future__ import annotations

import os

from swinginsight.ingest.adapters.akshare_news_feed import AkshareNewsFeed
from swinginsight.ingest.adapters.cninfo_news_feed import CninfoNewsFeed
from swinginsight.ingest.adapters.demo_news_feed import DemoNewsFeed
from swinginsight.ingest.adapters.eastmoney_news_feed import EastmoneyNewsFeed
from swinginsight.ingest.source_priority import parse_priority


def build_news_feeds(*, demo: bool, source_list: list[str] | None = None) -> list[tuple[object, str]]:
    if demo:
        return [(DemoNewsFeed(), "demo")]

    priorities = source_list or parse_priority(os.getenv("DATA_SOURCE_PRIORITY_NEWS"), ["cninfo", "eastmoney", "akshare"])
    feeds: list[tuple[object, str]] = []
    for source_name in priorities:
        if source_name == "cninfo":
            feeds.append((CninfoNewsFeed(), source_name))
            continue
        if source_name == "eastmoney":
            feeds.append((EastmoneyNewsFeed(), source_name))
            continue
        if source_name == "akshare":
            feeds.append((AkshareNewsFeed(), source_name))
            continue
        if source_name == "demo":
            feeds.append((DemoNewsFeed(), source_name))

    if not feeds:
        raise ValueError("No supported news source configured")
    return feeds
