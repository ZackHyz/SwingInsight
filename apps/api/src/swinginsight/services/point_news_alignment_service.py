from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.news import NewsProcessed, NewsRaw, PointNewsMap
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.domain.news.dedupe import dedupe_news_items


@dataclass(slots=True, frozen=True)
class PointNewsTimelineItem:
    news_id: int
    title: str
    summary: str | None
    source_name: str | None
    relation_type: str
    distance_days: int | None
    news_date: date | None
    category: str | None = None
    sub_category: str | None = None
    sentiment: str | None = None
    heat_level: str | None = None
    keyword_list: list[str] | None = None


def align_point_news(session: Session, point_id: int, before_days: int = 5, after_days: int = 5) -> list[PointNewsMap]:
    point = session.scalar(select(TurningPoint).where(TurningPoint.id == point_id))
    if point is None:
        raise ValueError(f"turning point not found: {point_id}")

    news_rows = session.scalars(
        select(NewsRaw)
        .where(
            NewsRaw.stock_code == point.stock_code,
            NewsRaw.news_date.is_not(None),
            NewsRaw.news_date >= point.point_date.fromordinal(point.point_date.toordinal() - before_days),
            NewsRaw.news_date <= point.point_date.fromordinal(point.point_date.toordinal() + after_days),
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

    session.execute(delete(PointNewsMap).where(PointNewsMap.point_id == point_id))

    aligned_rows: list[PointNewsMap] = []
    news_by_id = {row.id: row for row in news_rows}
    for candidate in candidates:
        news_row = news_by_id[int(candidate["id"])]
        relation_type = classify_point_news_relation(
            news_date=news_row.news_date,
            point_date=point.point_date,
            point_type=point.point_type,
            before_days=before_days,
            after_days=after_days,
        )
        if relation_type is None:
            continue

        distance_days = (news_row.news_date - point.point_date).days if news_row.news_date else None
        row = PointNewsMap(
            point_id=point.id,
            news_id=news_row.id,
            stock_code=point.stock_code,
            point_type=point.point_type,
            relation_type=relation_type,
            anchor_date=point.point_date,
            distance_days=distance_days,
            weight_score=1.0,
        )
        session.add(row)
        aligned_rows.append(row)

    session.flush()
    return aligned_rows


def classify_point_news_relation(
    *,
    news_date: date | None,
    point_date: date,
    point_type: str,
    before_days: int,
    after_days: int,
) -> str | None:
    if news_date is None:
        return None
    distance_days = (news_date - point_date).days
    if -before_days <= distance_days < 0:
        return f"before_{point_type}"
    if 0 < distance_days <= after_days:
        return f"after_{point_type}"
    return None


def get_point_timeline(session: Session, point_id: int) -> list[PointNewsTimelineItem]:
    rows = session.execute(
        select(PointNewsMap, NewsRaw, NewsProcessed)
        .join(NewsRaw, NewsRaw.id == PointNewsMap.news_id)
        .outerjoin(NewsProcessed, NewsProcessed.news_id == NewsRaw.id)
        .where(PointNewsMap.point_id == point_id)
        .order_by(NewsRaw.news_date.asc(), NewsRaw.id.asc())
    ).all()
    return [
        PointNewsTimelineItem(
            news_id=news.id,
            title=news.title,
            summary=news.summary,
            source_name=news.source_name,
            relation_type=mapping.relation_type,
            distance_days=mapping.distance_days,
            news_date=news.news_date,
            category=processed.category if processed is not None else None,
            sub_category=processed.sub_category if processed is not None else None,
            sentiment=processed.sentiment if processed is not None else news.sentiment,
            heat_level=processed.heat_level if processed is not None else None,
            keyword_list=processed.keyword_list if processed is not None else None,
        )
        for mapping, news, processed in rows
    ]
