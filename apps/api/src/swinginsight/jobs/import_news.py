from __future__ import annotations

from datetime import date

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.news_importer import NewsImporter
from swinginsight.services.news_source_service import build_news_feeds


def import_news(
    stock_code: str,
    start: date | None = None,
    end: date | None = None,
    *,
    demo: bool = False,
    source_list: list[str] | None = None,
) -> int:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        total = 0
        for feed, source_name in build_news_feeds(demo=demo, source_list=source_list):
            importer = NewsImporter(session=session, feed=feed, source_name=source_name)
            total += importer.run(stock_code=stock_code, start=start, end=end)
        return total
