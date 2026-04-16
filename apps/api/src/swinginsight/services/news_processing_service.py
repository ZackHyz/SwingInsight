from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import NewsProcessed, NewsRaw
from swinginsight.domain.news.classifier import classify_title
from swinginsight.domain.news.normalize import normalize_title
from swinginsight.domain.news.tagging import build_tags
from swinginsight.services.news_sentiment_service import NewsSentimentService


@dataclass(slots=True, frozen=True)
class NewsProcessingResult:
    processed_count: int
    duplicates: int
    sentiment_results: int = 0
    event_results: int = 0
    conflict_news: int = 0


class NewsProcessingService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def process_batch(self, news_ids: list[int]) -> NewsProcessingResult:
        rows = self.session.scalars(select(NewsRaw).where(NewsRaw.id.in_(news_ids)).order_by(NewsRaw.id.asc())).all()
        grouped = self._group_rows(rows)
        processed_count = 0
        duplicates = 0
        sentiment_results = 0
        event_results = 0
        conflict_news = 0
        processed_at = datetime.now(UTC).replace(tzinfo=None)
        sentiment_service = NewsSentimentService(self.session)

        for group_rows in grouped.values():
            main_row = group_rows[0]
            duplicate_group_id = f"dup-{main_row.id}" if len(group_rows) > 1 else None
            for index, row in enumerate(group_rows):
                sentiment_persistence = sentiment_service.persist_for_news(row, duplicate_count=len(group_rows))
                tags = build_tags(
                    title=row.title,
                    summary=row.summary,
                    source_type=row.source_type,
                    duplicate_count=len(group_rows),
                    sentiment_result=sentiment_persistence.sentiment_score,
                )
                row.is_duplicate = index > 0
                row.duplicate_group_id = duplicate_group_id
                row.main_news_id = main_row.id if index > 0 else None
                row.is_parsed = True
                row.parse_status = "processed"
                row.sentiment = tags.sentiment

                classification = classify_title(row.title, source_type=row.source_type)
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
                sentiment_results += sentiment_persistence.sentiment_result_count
                event_results += sentiment_persistence.event_result_count
                if sentiment_persistence.sentiment_score.event_conflict_flag:
                    conflict_news += 1
                if row.is_duplicate:
                    duplicates += 1

        self.session.commit()
        return NewsProcessingResult(
            processed_count=processed_count,
            duplicates=duplicates,
            sentiment_results=sentiment_results,
            event_results=event_results,
            conflict_news=conflict_news,
        )

    def _group_rows(self, rows: list[NewsRaw]) -> dict[tuple[str | None, str, object], list[NewsRaw]]:
        grouped: dict[tuple[str | None, str, object], list[NewsRaw]] = {}
        for row in rows:
            key = (row.stock_code, normalize_title(row.title), row.news_date)
            grouped.setdefault(key, []).append(row)
        return grouped
