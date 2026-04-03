from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.base import Base
from swinginsight.db.models.market_data import TaskRunLog
from swinginsight.db.models.news import NewsRaw
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.news_processing_service import NewsProcessingService


@dataclass(slots=True, frozen=True)
class ProcessNewsResult:
    processed_count: int
    duplicates: int
    sentiment_results: int = 0
    event_results: int = 0
    conflict_news: int = 0


def process_news(
    stock_code: str,
    start: date | None = None,
    end: date | None = None,
    *,
    session: Session | None = None,
) -> ProcessNewsResult:
    started_at = datetime.now(UTC)

    def run(current_session: Session) -> ProcessNewsResult:
        query = select(NewsRaw.id).where(NewsRaw.stock_code == stock_code)
        if start is not None:
            query = query.where(NewsRaw.news_date.is_not(None), NewsRaw.news_date >= start)
        if end is not None:
            query = query.where(NewsRaw.news_date.is_not(None), NewsRaw.news_date <= end)
        news_ids = list(current_session.scalars(query.order_by(NewsRaw.id.asc())).all())
        result = NewsProcessingService(current_session).process_batch(news_ids)
        finished_at = datetime.now(UTC)
        current_session.add(
            TaskRunLog(
                task_name=f"process-news:{stock_code}",
                task_type="process_news",
                target_code=stock_code,
                status="success",
                start_time=started_at,
                end_time=finished_at,
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                input_params_json={
                    "stock_code": stock_code,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                },
                result_summary=(
                    f"processed={result.processed_count},duplicates={result.duplicates},"
                    f"sentiment_results={result.sentiment_results},event_results={result.event_results},"
                    f"conflict_news={result.conflict_news}"
                ),
            )
        )
        current_session.commit()
        return ProcessNewsResult(
            processed_count=result.processed_count,
            duplicates=result.duplicates,
            sentiment_results=result.sentiment_results,
            event_results=result.event_results,
            conflict_news=result.conflict_news,
        )

    if session is not None:
        return run(session)

    Base.metadata.create_all(get_engine())
    with session_scope() as current_session:
        return run(current_session)
