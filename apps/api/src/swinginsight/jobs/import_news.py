from __future__ import annotations

from datetime import date

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.adapters.akshare_news_feed import AkshareNewsFeed
from swinginsight.ingest.news_importer import NewsImporter


def import_news(stock_code: str, start: date | None = None, end: date | None = None) -> int:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        importer = NewsImporter(session=session, feed=AkshareNewsFeed(), source_name="akshare")
        return importer.run(stock_code=stock_code, start=start, end=end)
