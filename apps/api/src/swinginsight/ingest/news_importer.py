from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import TaskRunLog
from swinginsight.db.models.news import NewsRaw
from swinginsight.ingest.ports import NewsFeed


class NewsImporter:
    def __init__(self, session: Session, feed: NewsFeed, source_name: str | None = None) -> None:
        self.session = session
        self.feed = feed
        self.source_name = source_name or feed.__class__.__name__

    def run(self, stock_code: str, start: date | None = None, end: date | None = None) -> int:
        started_at = datetime.now(UTC)
        rows = self.feed.fetch_news(stock_code=stock_code, start=start, end=end)
        inserted = 0
        updated = 0
        for row in rows:
            normalized = self._normalize_payload(row)
            existing = self._find_existing_row(normalized)
            if existing is None:
                self.session.add(NewsRaw(**normalized))
                inserted += 1
                continue

            changed = False
            for field, value in normalized.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                updated += 1
        finished_at = datetime.now(UTC)
        self.session.add(
            TaskRunLog(
                task_name=f"import-news:{stock_code}",
                task_type="import_news",
                target_code=stock_code,
                status="success",
                start_time=started_at,
                end_time=finished_at,
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                input_params_json={
                    "stock_code": stock_code,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "source": self.source_name,
                },
                result_summary=f"inserted={inserted},updated={updated}",
            )
        )
        self.session.commit()
        return len(rows)

    def _find_existing_row(self, payload: dict[str, Any]) -> NewsRaw | None:
        news_uid = payload.get("news_uid")
        if news_uid:
            existing = self.session.scalar(select(NewsRaw).where(NewsRaw.news_uid == news_uid))
            if existing is not None:
                return existing

        url = payload.get("url")
        title = payload.get("title")
        publish_time = payload.get("publish_time")
        if url:
            existing = self.session.scalar(select(NewsRaw).where(NewsRaw.url == url))
            if existing is not None:
                return existing

        if title and publish_time:
            return self.session.scalar(
                select(NewsRaw).where(
                    NewsRaw.stock_code == payload.get("stock_code"),
                    NewsRaw.publish_time == publish_time,
                    or_(NewsRaw.title == title, NewsRaw.url == url),
                )
            )
        return None

    def _normalize_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {
            "news_uid": payload.get("news_uid"),
            "stock_code": payload.get("stock_code"),
            "title": payload["title"],
            "summary": payload.get("summary"),
            "content": payload.get("content"),
            "publish_time": payload["publish_time"],
            "news_date": payload.get("news_date"),
            "source_name": payload.get("source_name", self.source_name),
            "source_type": payload.get("source_type"),
            "url": payload.get("url"),
            "related_industry": payload.get("related_industry"),
            "related_concept": payload.get("related_concept"),
            "sentiment": payload.get("sentiment"),
            "news_type": payload.get("news_type"),
            "keywords": payload.get("keywords"),
            "is_duplicate": bool(payload.get("is_duplicate", False)),
            "duplicate_group_id": payload.get("duplicate_group_id"),
            "main_news_id": payload.get("main_news_id"),
            "raw_json": payload.get("raw_json"),
            "fetch_time": payload.get("fetch_time", datetime.now(UTC).replace(tzinfo=None)),
            "is_parsed": bool(payload.get("is_parsed", False)),
            "parse_status": payload.get("parse_status", "pending"),
            "data_source": payload.get("data_source", self.source_name),
        }
