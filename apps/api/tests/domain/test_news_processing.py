from __future__ import annotations

from datetime import UTC, date, datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    import swinginsight.db.models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def seed_duplicate_news(session):
    from swinginsight.db.models.news import NewsRaw

    session.add_all(
        [
            NewsRaw(
                news_uid="dup-1",
                stock_code="000001",
                title="2025年业绩预告同比扭亏",
                summary="首发摘要",
                content="首发正文",
                publish_time=datetime(2024, 1, 2, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 2),
                source_name="cninfo",
                source_type="announcement",
                url="https://example.com/dup-1",
                data_source="fake",
                fetch_time=datetime(2024, 1, 2, 9, 5, tzinfo=UTC).replace(tzinfo=None),
                is_parsed=False,
                parse_status="pending",
            ),
            NewsRaw(
                news_uid="dup-2",
                stock_code="000001",
                title="2025年业绩预告同比扭亏",
                summary="转载摘要",
                content="转载正文",
                publish_time=datetime(2024, 1, 2, 9, 30, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 2),
                source_name="cninfo",
                source_type="announcement",
                url="https://example.com/dup-2",
                data_source="fake",
                fetch_time=datetime(2024, 1, 2, 9, 35, tzinfo=UTC).replace(tzinfo=None),
                is_parsed=False,
                parse_status="pending",
            ),
        ]
    )
    session.commit()


def test_process_news_marks_duplicate_group_and_main_news() -> None:
    from swinginsight.db.models.news import NewsProcessed, NewsRaw
    from swinginsight.services.news_processing_service import NewsProcessingService

    session = build_session()
    seed_duplicate_news(session)

    result = NewsProcessingService(session).process_batch([1, 2])

    assert result.processed_count == 2
    assert result.duplicates >= 1

    processed = session.scalars(select(NewsProcessed).order_by(NewsProcessed.news_id.asc())).all()
    assert len(processed) == 2
    assert processed[0].category == "announcement"
    assert processed[0].sub_category == "earnings"

    raw_rows = session.scalars(select(NewsRaw).order_by(NewsRaw.id.asc())).all()
    assert raw_rows[0].is_parsed is True
    assert raw_rows[0].parse_status == "processed"
    assert raw_rows[1].is_duplicate is True
    assert raw_rows[1].main_news_id == raw_rows[0].id


def test_rule_classifier_maps_business_categories() -> None:
    from swinginsight.domain.news.classifier import classify_title

    earnings = classify_title("2025年业绩预告同比扭亏")
    contract = classify_title("签署重大订单协议")
    risk = classify_title("异常波动及风险提示公告")
    disclosure = classify_title("包钢股份关于召开2026年第一次临时股东会的通知", source_type="announcement")
    resolution = classify_title("包钢股份第七届董事会第四十三次会议决议公告", source_type="announcement")
    material = classify_title("包钢股份2026年第一次临时股东会材料", source_type="announcement")

    assert earnings.category == "announcement"
    assert earnings.sub_category == "earnings"
    assert contract.sub_category == "order_contract"
    assert risk.sub_category == "risk_alert"
    assert disclosure.category == "announcement"
    assert disclosure.sub_category == "governance"
    assert resolution.sub_category == "governance"
    assert material.sub_category == "governance"


def test_process_news_collapses_same_day_cross_source_duplicates() -> None:
    from swinginsight.db.models.news import NewsRaw
    from swinginsight.services.news_processing_service import NewsProcessingService

    session = build_session()
    session.add_all(
        [
            NewsRaw(
                news_uid="cross-source-1",
                stock_code="000001",
                title="公司签署重大订单协议",
                summary="公告渠道披露",
                content=None,
                publish_time=datetime(2024, 1, 3, 9, 0, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 3),
                source_name="cninfo",
                source_type="announcement",
                url="https://example.com/cross-source-1",
                data_source="fake",
                fetch_time=datetime(2024, 1, 3, 9, 5, tzinfo=UTC).replace(tzinfo=None),
                is_parsed=False,
                parse_status="pending",
            ),
            NewsRaw(
                news_uid="cross-source-2",
                stock_code="000001",
                title="公司签署重大订单协议",
                summary="媒体渠道转载",
                content=None,
                publish_time=datetime(2024, 1, 3, 9, 20, tzinfo=UTC).replace(tzinfo=None),
                news_date=date(2024, 1, 3),
                source_name="eastmoney",
                source_type="news",
                url="https://example.com/cross-source-2",
                data_source="fake",
                fetch_time=datetime(2024, 1, 3, 9, 25, tzinfo=UTC).replace(tzinfo=None),
                is_parsed=False,
                parse_status="pending",
            ),
        ]
    )
    session.commit()

    result = NewsProcessingService(session).process_batch([1, 2])

    assert result.processed_count == 2
    assert result.duplicates == 1
