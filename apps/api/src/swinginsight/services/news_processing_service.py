from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import NewsProcessed, NewsRaw
from swinginsight.domain.news.classifier import classify_title
from swinginsight.domain.news.normalize import normalize_title
from swinginsight.domain.news.tagging import build_tags


@dataclass(slots=True, frozen=True)
class NewsProcessingResult:
    processed_count: int
    duplicates: int


class NewsProcessingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def process_batch(self, news_ids: list[int]) -> NewsProcessingResult:
        rows = self.session.scalars(select(NewsRaw).where(NewsRaw.id.in_(news_ids)).order_by(NewsRaw.id.asc())).all()
        grouped = self._group_rows(rows)
        processed_count = 0
        duplicates = 0
        processed_at = datetime.now(UTC).replace(tzinfo=None)

        for group_rows in grouped.values():
            main_row = group_rows[0]
            duplicate_group_id = f"dup-{main_row.id}" if len(group_rows) > 1 else None
            tags = build_tags(
                title=main_row.title,
                source_type=main_row.source_type,
                duplicate_count=len(group_rows),
            )
            for index, row in enumerate(group_rows):
                row.is_duplicate = index > 0
                row.duplicate_group_id = duplicate_group_id
                row.main_news_id = main_row.id if index > 0 else None
                row.is_parsed = True
                row.parse_status = "processed"
                row.sentiment = tags.sentiment

                classification = classify_title(row.title)
                row.news_type = classification.sub_category
                row.keywords = ",".join(classification.keywords)

                existing = self.session.scalar(select(NewsProcessed).where(NewsProcessed.news_id == row.id))
                if existing is None:
                    existing = NewsProcessed(news_id=row.id)
                    self.session.add(existing)

                existing.stock_code = row.stock_code
                existing.clean_title = normalize_title(row.title)
                existing.clean_summary = row.summary
                existing.category = classification.category
                existing.sub_category = classification.sub_category
                existing.sentiment = tags.sentiment
                existing.heat_level = tags.heat_level
                existing.keyword_list = classification.keywords
                existing.tag_list = tags.tag_list
                existing.is_duplicate = row.is_duplicate
                existing.duplicate_group_id = duplicate_group_id
                existing.main_news_id = main_row.id if index > 0 else None
                existing.processed_at = processed_at

                processed_count += 1
                if row.is_duplicate:
                    duplicates += 1

        self.session.commit()
        return NewsProcessingResult(processed_count=processed_count, duplicates=duplicates)

    def _group_rows(self, rows: list[NewsRaw]) -> dict[tuple[str, str | None, object], list[NewsRaw]]:
        grouped: dict[tuple[str, str | None, object], list[NewsRaw]] = {}
        for row in rows:
            key = (normalize_title(row.title), row.source_name, row.news_date)
            grouped.setdefault(key, []).append(row)
        return grouped
