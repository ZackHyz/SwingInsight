from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_extract_events_splits_multiple_financial_events() -> None:
    from swinginsight.domain.news.events import extract_events

    events = extract_events("公司发布业绩预增公告，同时控股股东拟减持。")

    assert [event.event_type for event in events] == ["earnings", "capital_action"]
    assert [event.event_polarity for event in events] == ["positive", "negative"]


def test_score_news_sentiment_aggregates_conflicting_events() -> None:
    from swinginsight.domain.news.events import EventSignal
    from swinginsight.domain.news.sentiment import score_news_sentiment

    result = score_news_sentiment(
        title="公司发布业绩预增公告，同时控股股东拟减持",
        summary=None,
        source_type="announcement",
        duplicate_count=1,
        events=[
            EventSignal(
                sentence_index=0,
                sentence_text="公司发布业绩预增公告",
                event_type="earnings",
                event_polarity="positive",
                event_strength=4,
                trigger_keywords=["业绩预增"],
            ),
            EventSignal(
                sentence_index=1,
                sentence_text="控股股东拟减持",
                event_type="capital_action",
                event_polarity="negative",
                event_strength=3,
                trigger_keywords=["减持"],
            ),
        ],
    )

    assert result.sentiment_label == "neutral"
    assert result.event_conflict_flag is True
    assert result.sentiment_score_base != 0


def test_extract_events_matches_real_governance_announcement_titles() -> None:
    from swinginsight.domain.news.events import extract_events

    resolution_events = extract_events("包钢股份第七届董事会第四十三次会议决议公告")
    notice_events = extract_events("包钢股份关于召开2026年第一次临时股东会的通知")
    material_events = extract_events("包钢股份2026年第一次临时股东会材料")

    assert [event.event_type for event in resolution_events] == ["governance"]
    assert [event.event_type for event in notice_events] == ["governance"]
    assert [event.event_type for event in material_events] == ["governance"]


def test_extract_events_source_aware_confidence_for_same_event_type() -> None:
    from swinginsight.domain.news.events import extract_events

    announcement_events = extract_events(
        "公司公告：签署重大订单协议",
        source_type="announcement",
    )
    media_events = extract_events(
        "媒体称公司签署重大订单协议",
        source_type="news",
    )

    announcement_order_event = next(event for event in announcement_events if event.event_type == "order_contract")
    media_order_event = next(event for event in media_events if event.event_type == "order_contract")

    assert announcement_order_event.signal_source == "announcement"
    assert media_order_event.signal_source == "media"
    assert announcement_order_event.confidence > media_order_event.confidence


def test_extract_events_suppresses_governance_template_noise() -> None:
    from swinginsight.domain.news.events import extract_events

    events = extract_events(
        "关于召开2026年第一次临时股东会的通知及风险提示公告",
        source_type="announcement",
    )

    assert [event.event_type for event in events] == ["governance"]
    assert [event.event_polarity for event in events] == ["neutral"]
