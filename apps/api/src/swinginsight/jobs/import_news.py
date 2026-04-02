from __future__ import annotations

from datetime import date, timedelta

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.news_importer import NewsImporter
from swinginsight.services.news_source_service import build_news_feeds
from sqlalchemy.orm import Session

DEFAULT_NEWS_REFRESH_DAYS = 7


def resolve_news_refresh_window(
    *,
    start: date | None = None,
    end: date | None = None,
    anchor_date: date | None = None,
) -> tuple[date, date]:
    resolved_end = end or anchor_date or date.today()
    resolved_start = start or (resolved_end - timedelta(days=DEFAULT_NEWS_REFRESH_DAYS))
    return resolved_start, resolved_end


def import_news(
    stock_code: str,
    start: date | None = None,
    end: date | None = None,
    *,
    demo: bool = False,
    source_list: list[str] | None = None,
    session: Session | None = None,
) -> int:
    start_date, end_date = resolve_news_refresh_window(start=start, end=end)

    def run(current_session: Session) -> int:
        total = 0
        for feed, source_name in build_news_feeds(demo=demo, source_list=source_list):
            importer = NewsImporter(session=current_session, feed=feed, source_name=source_name)
            total += importer.run(stock_code=stock_code, start=start_date, end=end_date)
        return total

    if session is not None:
        return run(session)

    Base.metadata.create_all(get_engine())
    with session_scope() as current_session:
        return run(current_session)
