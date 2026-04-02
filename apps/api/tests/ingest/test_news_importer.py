from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


class FakeNewsFeed:
    def fetch_news(self, stock_code: str, start: date | None, end: date | None):
        return [
            {
                "news_uid": "news-1",
                "stock_code": stock_code,
                "title": "2025年业绩预告同比扭亏",
                "summary": "首版摘要",
                "content": "首版正文",
                "publish_time": datetime(2024, 1, 2, 9, 0, 0),
                "news_date": date(2024, 1, 2),
                "source_name": "fake-feed",
                "source_type": "announcement",
                "url": "https://example.com/news-1",
                "raw_json": {"id": "news-1", "title": "2025年业绩预告同比扭亏"},
                "data_source": "fake",
            },
            {
                "news_uid": "news-2",
                "stock_code": stock_code,
                "title": "签署重大订单协议",
                "summary": "二号摘要",
                "content": "二号正文",
                "publish_time": datetime(2024, 1, 3, 10, 0, 0),
                "news_date": date(2024, 1, 3),
                "source_name": "fake-feed",
                "source_type": "media_news",
                "url": "https://example.com/news-2",
                "raw_json": {"id": "news-2", "title": "签署重大订单协议"},
                "data_source": "fake",
            },
        ]


class FakeNewsFeedUpdated(FakeNewsFeed):
    def fetch_news(self, stock_code: str, start: date | None, end: date | None):
        rows = super().fetch_news(stock_code, start, end)
        rows[0]["summary"] = "更新后的摘要"
        rows[0]["content"] = "更新后的正文"
        return rows


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def test_news_importer_upserts_rows_and_sets_processing_metadata() -> None:
    from swinginsight.db.models.market_data import TaskRunLog
    from swinginsight.db.models.news import NewsRaw
    from swinginsight.ingest.news_importer import NewsImporter

    session = build_session()
    importer = NewsImporter(session=session, feed=FakeNewsFeed(), source_name="fake")

    inserted = importer.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert inserted == 2
    rows = session.scalars(select(NewsRaw).order_by(NewsRaw.news_uid.asc())).all()
    assert len(rows) == 2
    assert rows[0].fetch_time is not None
    assert rows[0].is_parsed is False
    assert rows[0].parse_status == "pending"
    assert rows[0].raw_json == {"id": "news-1", "title": "2025年业绩预告同比扭亏"}

    updater = NewsImporter(session=session, feed=FakeNewsFeedUpdated(), source_name="fake")
    updated = updater.run(stock_code="000001", start=date(2024, 1, 1), end=date(2024, 1, 31))

    assert updated == 2
    rows_after_update = session.scalars(select(NewsRaw).order_by(NewsRaw.news_uid.asc())).all()
    assert len(rows_after_update) == 2
    assert rows_after_update[0].summary == "更新后的摘要"

    logs = session.scalars(select(TaskRunLog).order_by(TaskRunLog.id.asc())).all()
    assert len(logs) == 2
    assert logs[0].task_type == "import_news"
