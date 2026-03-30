from __future__ import annotations

from sqlalchemy.orm import Session

from swinginsight.services.segment_news_alignment_service import get_segment_timeline


def get_segment_news_payload(session: Session, segment_id: int) -> list[dict[str, object]]:
    return [
        {
            "news_id": item.news_id,
            "title": item.title,
            "summary": item.summary,
            "source_name": item.source_name,
            "relation_type": item.relation_type,
            "distance_days": item.distance_days,
            "news_date": item.news_date.isoformat() if item.news_date else None,
        }
        for item in get_segment_timeline(session, segment_id)
    ]
