from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import NewsRaw, SegmentNewsMap
from swinginsight.db.models.segment import SwingSegment
from swinginsight.domain.news.dedupe import dedupe_news_items


@dataclass(slots=True, frozen=True)
class SegmentNewsTimelineItem:
    news_id: int
    title: str
    summary: str | None
    source_name: str | None
    relation_type: str
    distance_days: int | None
    news_date: date | None


def align_segment_news(session: Session, segment_id: int, before_days: int = 5, after_days: int = 5) -> list[SegmentNewsMap]:
    segment = session.scalar(select(SwingSegment).where(SwingSegment.id == segment_id))
    if segment is None:
        raise ValueError(f"segment not found: {segment_id}")

    news_rows = session.scalars(
        select(NewsRaw)
        .where(
            NewsRaw.stock_code == segment.stock_code,
            NewsRaw.news_date.is_not(None),
            NewsRaw.news_date >= segment.start_date.fromordinal(segment.start_date.toordinal() - before_days),
            NewsRaw.news_date <= segment.end_date.fromordinal(segment.end_date.toordinal() + after_days),
        )
        .order_by(NewsRaw.news_date.asc(), NewsRaw.id.asc())
    ).all()

    candidates = dedupe_news_items(
        [
            {
                "id": row.id,
                "title": row.title,
                "summary": row.summary,
                "source_name": row.source_name,
                "news_date": row.news_date,
            }
            for row in news_rows
        ]
    )

    session.execute(delete(SegmentNewsMap).where(SegmentNewsMap.segment_id == segment_id))

    aligned_rows: list[SegmentNewsMap] = []
    news_by_id = {row.id: row for row in news_rows}
    for candidate in candidates:
        news_row = news_by_id[int(candidate["id"])]
        relation_type, anchor_date = classify_news_relation(
            news_date=news_row.news_date,
            start_date=segment.start_date,
            end_date=segment.end_date,
            start_point_type=segment.start_point_type,
            end_point_type=segment.end_point_type,
            before_days=before_days,
            after_days=after_days,
        )
        if relation_type is None or anchor_date is None:
            continue

        distance_days = (news_row.news_date - anchor_date).days if news_row.news_date else None
        row = SegmentNewsMap(
            segment_id=segment.id,
            news_id=news_row.id,
            stock_code=segment.stock_code,
            relation_type=relation_type,
            window_type="point_window" if relation_type != "inside_segment" else "segment_body",
            anchor_date=anchor_date,
            distance_days=distance_days,
            weight_score=1.0,
        )
        session.add(row)
        aligned_rows.append(row)

    session.flush()
    return aligned_rows


def classify_news_relation(
    *,
    news_date: date | None,
    start_date: date,
    end_date: date,
    start_point_type: str,
    end_point_type: str,
    before_days: int,
    after_days: int,
) -> tuple[str | None, date | None]:
    if news_date is None:
        return None, None

    start_offset = (news_date - start_date).days
    end_offset = (news_date - end_date).days

    if -before_days <= start_offset < 0:
        return f"before_{start_point_type}", start_date
    if 0 <= start_offset <= (end_date - start_date).days:
        return "inside_segment", start_date
    if 0 < end_offset <= after_days:
        return f"after_{end_point_type}", end_date
    return None, None


def get_segment_timeline(session: Session, segment_id: int) -> list[SegmentNewsTimelineItem]:
    rows = session.execute(
        select(SegmentNewsMap, NewsRaw)
        .join(NewsRaw, NewsRaw.id == SegmentNewsMap.news_id)
        .where(SegmentNewsMap.segment_id == segment_id)
        .order_by(NewsRaw.news_date.asc(), NewsRaw.id.asc())
    ).all()
    return [
        SegmentNewsTimelineItem(
            news_id=news.id,
            title=news.title,
            summary=news.summary,
            source_name=news.source_name,
            relation_type=mapping.relation_type,
            distance_days=mapping.distance_days,
            news_date=news.news_date,
        )
        for mapping, news in rows
    ]
