from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session_factory():
    from swinginsight.db.base import Base

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)


def seed_research_data(session: Session) -> None:
    from swinginsight.db.models.market_data import DailyPrice, TradeRecord
    from swinginsight.db.models.news import (
        NewsEventResult,
        NewsProcessed,
        NewsRaw,
        NewsSentimentResult,
        PointNewsMap,
        SegmentNewsMap,
    )
    from swinginsight.db.models.segment import SegmentFeature, SwingSegment
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.db.models.prediction import PredictionResult
    from swinginsight.db.models.turning_point import TurningPoint

    session.add(
        StockBasic(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=["finance", "bluechip"],
        )
    )
    prices = [
        (date(2024, 1, 2), 10.0, 10.2, 9.8, 10.0),
        (date(2024, 1, 3), 9.8, 9.9, 9.2, 9.4),
        (date(2024, 1, 4), 9.2, 9.3, 8.7, 8.8),
        (date(2024, 1, 5), 8.9, 9.9, 8.9, 9.7),
        (date(2024, 1, 8), 9.8, 10.7, 9.7, 10.6),
        (date(2024, 1, 9), 10.4, 10.5, 9.6, 9.8),
        (date(2024, 1, 10), 9.4, 9.5, 8.8, 8.9),
        (date(2024, 1, 11), 9.1, 10.0, 9.0, 9.9),
        (date(2024, 1, 12), 10.2, 11.0, 10.1, 10.9),
    ]
    for trade_date, open_price, high_price, low_price, close_price in prices:
        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                adj_type="qfq",
                data_source="test",
            )
        )

    session.add_all(
        [
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 4),
                point_type="trough",
                point_price=8.8,
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 8),
                point_type="peak",
                point_price=10.6,
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 4),
                point_type="trough",
                point_price=8.8,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
            TurningPoint(
                stock_code="000001",
                point_date=date(2024, 1, 8),
                point_type="peak",
                point_price=10.6,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
        ]
    )
    session.add(
        SwingSegment(
            segment_uid="000001:2024-01-04:2024-01-08:manual:latest",
            stock_code="000001",
            start_date=date(2024, 1, 4),
            end_date=date(2024, 1, 8),
            start_point_type="trough",
            end_point_type="peak",
            start_price=8.8,
            end_price=10.6,
            pct_change=20.4545,
            duration_days=4,
            trend_direction="up",
            segment_type="up_swing",
            source_version="manual:latest",
            is_final=True,
        )
    )
    session.flush()
    session.add_all(
        [
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="technical",
                feature_name="pct_change",
                feature_value_num=20.4545,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="technical",
                feature_name="duration_days",
                feature_value_num=4,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="technical",
                feature_name="max_drawdown_pct",
                feature_value_num=-2.0,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="technical",
                feature_name="volume_ratio_5d",
                feature_value_num=1.5,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="technical",
                feature_name="ma5_above_ma20",
                feature_value_num=1.0,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="technical",
                feature_name="macd_cross_flag",
                feature_value_num=1.0,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="news",
                feature_name="positive_news_ratio",
                feature_value_num=0.7,
                version_code="feature:v1",
            ),
            SegmentFeature(
                segment_id=1,
                stock_code="000001",
                feature_group="news",
                feature_name="duplicate_news_ratio",
                feature_value_num=0.0,
                version_code="feature:v1",
            ),
        ]
    )
    session.add(
        PredictionResult(
            stock_code="000001",
            predict_date=date(2024, 1, 12),
            current_state="主升初期",
            up_prob_5d=0.6,
            flat_prob_5d=0.2,
            down_prob_5d=0.2,
            up_prob_10d=0.58,
            flat_prob_10d=0.22,
            down_prob_10d=0.2,
            up_prob_20d=0.5,
            flat_prob_20d=0.25,
            down_prob_20d=0.25,
            similarity_topn_json=[],
            key_features_json={"volume_ratio_5d": 1.5},
            risk_flags_json={"pullback_risk": "low"},
            model_version="prediction:v1",
            summary="stub",
        )
    )
    session.add(
        TradeRecord(
            stock_code="000001",
            trade_date=date(2024, 1, 5),
            trade_type="buy",
            price=9.7,
            quantity=100,
            amount=970,
            strategy_tag="test",
            order_group_id="g1",
            note="seed buy",
            source="test",
        )
    )
    news = NewsRaw(
            stock_code="000001",
            title="Liquidity support boosts banks",
            summary="Positive catalyst near the rebound",
            content="demo",
            publish_time=date(2024, 1, 6),
            news_date=date(2024, 1, 6),
            source_name="wire",
            source_type="test",
            sentiment="positive",
            news_type="macro",
            is_duplicate=False,
            data_source="test",
        )
    recent_news = NewsRaw(
            stock_code="000001",
            title="Major shareholder plans reduction",
            summary="Capital action risk after the peak",
            content="demo",
            publish_time=date(2024, 1, 10),
            news_date=date(2024, 1, 10),
            source_name="wire",
            source_type="test",
            sentiment="negative",
            news_type="capital_action",
            is_duplicate=False,
            data_source="test",
        )
    session.add_all([news, recent_news])
    session.flush()
    session.add_all(
        [
            NewsProcessed(
                news_id=news.id,
                stock_code="000001",
                clean_title="liquidity support boosts banks",
                clean_summary="Positive catalyst near the rebound",
                category="announcement",
                sub_category="earnings",
                sentiment="positive",
                heat_level="medium",
                keyword_list=["support"],
                tag_list=["official"],
                is_duplicate=False,
            ),
            NewsProcessed(
                news_id=recent_news.id,
                stock_code="000001",
                clean_title="major shareholder plans reduction",
                clean_summary="Capital action risk after the peak",
                category="announcement",
                sub_category="capital_action",
                sentiment="negative",
                heat_level="high",
                keyword_list=["reduction"],
                tag_list=["official"],
                is_duplicate=False,
            ),
            NewsSentimentResult(
                news_id=news.id,
                stock_code="000001",
                sentiment_label="positive",
                sentiment_score_base=0.8,
                sentiment_score_adjusted=0.8,
                confidence_score=0.85,
                heat_score=0.65,
                market_context_score=0.0,
                position_context_score=0.0,
                event_conflict_flag=False,
                model_version="rules:v1",
            ),
            NewsSentimentResult(
                news_id=recent_news.id,
                stock_code="000001",
                sentiment_label="negative",
                sentiment_score_base=-0.6,
                sentiment_score_adjusted=-0.6,
                confidence_score=0.8,
                heat_score=0.8,
                market_context_score=0.0,
                position_context_score=0.0,
                event_conflict_flag=False,
                model_version="rules:v1",
            ),
            NewsEventResult(
                news_id=news.id,
                stock_code="000001",
                sentence_index=0,
                sentence_text="Liquidity support boosts banks",
                event_type="earnings",
                event_polarity="positive",
                event_strength=4,
                entity_main="000001",
                trigger_keywords=["support"],
                model_version="rules:v1",
            ),
            NewsEventResult(
                news_id=recent_news.id,
                stock_code="000001",
                sentence_index=0,
                sentence_text="Major shareholder plans reduction",
                event_type="capital_action",
                event_polarity="negative",
                event_strength=4,
                entity_main="000001",
                trigger_keywords=["reduction"],
                model_version="rules:v1",
            ),
            SegmentNewsMap(
                segment_id=1,
                news_id=news.id,
                stock_code="000001",
                relation_type="inside_segment",
                window_type="segment_body",
                anchor_date=date(2024, 1, 4),
                distance_days=2,
                weight_score=1.0,
            ),
            SegmentNewsMap(
                segment_id=1,
                news_id=recent_news.id,
                stock_code="000001",
                relation_type="after_peak",
                window_type="point_window",
                anchor_date=date(2024, 1, 8),
                distance_days=2,
                weight_score=1.0,
            ),
            PointNewsMap(
                point_id=4,
                news_id=news.id,
                stock_code="000001",
                point_type="peak",
                relation_type="before_peak",
                anchor_date=date(2024, 1, 8),
                distance_days=-2,
                weight_score=1.0,
            ),
            PointNewsMap(
                point_id=4,
                news_id=recent_news.id,
                stock_code="000001",
                point_type="peak",
                relation_type="after_peak",
                anchor_date=date(2024, 1, 8),
                distance_days=2,
                weight_score=1.0,
            ),
        ]
    )
    session.commit()


def test_get_stock_research_payload_contains_expected_sections(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed
    from swinginsight.services.stock_research_service import StockResearchService

    session_factory = build_session_factory()
    session = session_factory()
    seed_research_data(session)

    def fake_fetch_stock_metadata(self, stock_code: str) -> dict[str, object]:
        assert stock_code == "000001"
        return {
            "stock_code": "000001",
            "stock_name": "Ping An Bank",
            "market": "A",
            "industry": "Bank",
            "concept_tags": ["finance", "bluechip"],
        }

    def fake_fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, object]]:
        assert stock_code == "000001"
        rows = [
            (date(2024, 1, 2), 10.0, 10.2, 9.8, 10.0),
            (date(2024, 1, 3), 9.8, 9.9, 9.2, 9.4),
            (date(2024, 1, 4), 9.2, 9.3, 8.7, 8.8),
            (date(2024, 1, 5), 8.9, 9.9, 8.9, 9.7),
            (date(2024, 1, 8), 9.8, 10.7, 9.7, 10.6),
            (date(2024, 1, 9), 10.4, 10.5, 9.6, 9.8),
            (date(2024, 1, 10), 9.4, 9.5, 8.8, 8.9),
            (date(2024, 1, 11), 9.1, 10.0, 9.0, 9.9),
            (date(2024, 1, 12), 10.2, 11.0, 10.1, 10.9),
        ]
        return [
            {
                "stock_code": stock_code,
                "trade_date": trade_date,
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "close_price": close_price,
                "adj_type": "qfq",
                "volume": 1000,
                "amount": 100000.0,
                "turnover_rate": 1.2,
                "data_source": "akshare",
            }
            for trade_date, open_price, high_price, low_price, close_price in rows
        ]

    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_stock_metadata", fake_fetch_stock_metadata)
    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_daily_prices", fake_fetch_daily_prices)
    monkeypatch.setattr(StockResearchService, "ensure_stock_ready", lambda self, stock_code: True)

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/stocks/000001")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stock"]["stock_code"] == "000001"
    assert len(payload["prices"]) == 9
    assert len(payload["auto_turning_points"]) >= 2
    assert len(payload["final_turning_points"]) >= 2
    assert payload["current_state"]["label"]
    assert len(payload["trade_markers"]) == 1
    assert payload["trade_markers"][0]["trade_type"] == "buy"
    assert len(payload["news_items"]) == 2
    news_by_title = {item["title"]: item for item in payload["news_items"]}
    assert news_by_title["Liquidity support boosts banks"]["category"] == "announcement"
    assert news_by_title["Liquidity support boosts banks"]["source_type"] == "test"
    assert news_by_title["Liquidity support boosts banks"]["display_tags"] == ["当前波段内", "顶部前2日", "公告", "利多"]
    assert news_by_title["Liquidity support boosts banks"]["event_types"] == ["earnings"]
    assert news_by_title["Liquidity support boosts banks"]["event_conflict_flag"] is False
    assert news_by_title["Liquidity support boosts banks"]["sentiment_score_adjusted"] > 0.0
    assert news_by_title["Major shareholder plans reduction"]["event_types"] == ["capital_action"]
    assert news_by_title["Major shareholder plans reduction"]["event_conflict_flag"] is False
    assert news_by_title["Major shareholder plans reduction"]["sentiment_score_adjusted"] < -0.6
    assert payload["current_state"]["news_summary"]["window_news_count"] == 2.0
    assert payload["current_state"]["news_summary"]["announcement_count"] == 2.0
    assert payload["current_state"]["news_summary"]["positive_news_ratio"] == 0.5
    assert payload["current_state"]["news_summary"]["high_heat_count"] == 1.0
    assert payload["current_state"]["news_summary"]["avg_adjusted_sentiment"] < 0.0
    assert payload["current_state"]["news_summary"]["positive_event_count"] == 1.0
    assert payload["current_state"]["news_summary"]["negative_event_count"] == 1.0
    assert payload["current_state"]["news_summary"]["governance_event_count"] == 0.0


def test_get_segment_chart_window_returns_segment_context_with_pre_and_post_trading_days() -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.segment import SwingSegment
    from swinginsight.db.models.turning_point import TurningPoint

    session_factory = build_session_factory()
    session = session_factory()

    trade_dates = [date(2024, 1, 1) + timedelta(days=offset) for offset in range(30)]
    for offset, trade_date in enumerate(trade_dates):
        session.add(
            DailyPrice(
                stock_code="000009",
                trade_date=trade_date,
                open_price=10 + offset * 0.1,
                high_price=10.3 + offset * 0.1,
                low_price=9.8 + offset * 0.1,
                close_price=10.1 + offset * 0.1,
                volume=100000 + offset * 1000,
                adj_type="qfq",
                data_source="test",
            )
        )

    session.add_all(
        [
            TurningPoint(
                stock_code="000009",
                point_date=trade_dates[10],
                point_type="trough",
                point_price=10.8,
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code="000009",
                point_date=trade_dates[12],
                point_type="peak",
                point_price=11.6,
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code="000009",
                point_date=trade_dates[10],
                point_type="trough",
                point_price=10.8,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
            TurningPoint(
                stock_code="000009",
                point_date=trade_dates[12],
                point_type="peak",
                point_price=11.6,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
        ]
    )
    segment = SwingSegment(
        segment_uid="000009:2024-01-11:2024-01-13:manual:latest",
        stock_code="000009",
        start_date=trade_dates[10],
        end_date=trade_dates[12],
        start_point_type="trough",
        end_point_type="peak",
        start_price=10.8,
        end_price=11.6,
        pct_change=7.4,
        duration_days=2,
        trend_direction="up",
        segment_type="up_swing",
        source_version="manual:latest",
        is_final=True,
    )
    session.add(segment)
    session.commit()

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get(f"/segments/{segment.id}/chart")

    assert response.status_code == 200
    payload = response.json()
    assert payload["segment"]["id"] == segment.id
    assert payload["segment"]["stock_code"] == "000009"
    assert payload["highlight_range"] == {
        "start_date": trade_dates[10].isoformat(),
        "end_date": trade_dates[12].isoformat(),
    }
    assert len(payload["prices"]) == 23
    assert payload["prices"][0]["trade_date"] == trade_dates[0].isoformat()
    assert payload["prices"][-1]["trade_date"] == trade_dates[22].isoformat()
    assert len(payload["auto_turning_points"]) == 2
    assert len(payload["final_turning_points"]) == 2


def test_get_stock_research_payload_fetches_live_data_when_database_is_missing(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed
    from swinginsight.services.stock_research_service import research_window_start

    live_prices = [
        (date(2024, 1, 2), 1.44, 1.45, 1.40, 1.41),
        (date(2024, 1, 3), 1.41, 1.42, 1.35, 1.36),
        (date(2024, 1, 4), 1.35, 1.36, 1.28, 1.30),
        (date(2024, 1, 5), 1.30, 1.38, 1.29, 1.37),
        (date(2024, 1, 8), 1.37, 1.48, 1.36, 1.47),
        (date(2024, 1, 9), 1.47, 1.49, 1.40, 1.42),
        (date(2024, 1, 10), 1.42, 1.43, 1.33, 1.35),
        (date(2024, 1, 11), 1.35, 1.41, 1.34, 1.40),
        (date(2024, 1, 12), 1.40, 1.53, 1.39, 1.50),
    ]

    def fake_fetch_stock_metadata(self, stock_code: str) -> dict[str, object]:
        assert stock_code == "600157"
        return {
            "stock_code": stock_code,
            "stock_name": "永泰能源",
            "market": "A",
            "industry": "煤炭",
            "concept_tags": ["能源"],
        }

    def fake_fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, object]]:
        assert stock_code == "600157"
        assert start == research_window_start()
        assert end is None
        return [
            {
                "stock_code": stock_code,
                "trade_date": trade_date,
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "close_price": close_price,
                "adj_type": "qfq",
                "volume": 1000,
                "amount": 100000.0,
                "turnover_rate": 1.2,
                "data_source": "akshare",
            }
            for trade_date, open_price, high_price, low_price, close_price in live_prices
        ]

    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_stock_metadata", fake_fetch_stock_metadata)
    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_daily_prices", fake_fetch_daily_prices)

    session_factory = build_session_factory()
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/stocks/600157")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stock"]["stock_code"] == "600157"
    assert payload["stock"]["stock_name"] == "永泰能源"
    assert len(payload["prices"]) == len(live_prices)
    assert payload["final_turning_points"][-1]["point_date"] == date(2024, 1, 10).isoformat()
    assert payload["final_turning_points"][-1]["point_type"] == "trough"

    verification_session = session_factory()
    stored_stock = verification_session.scalar(select(StockBasic).where(StockBasic.stock_code == "600157"))
    stored_prices = verification_session.scalars(
        select(DailyPrice).where(DailyPrice.stock_code == "600157").order_by(DailyPrice.trade_date.asc())
    ).all()
    assert stored_stock is not None
    assert stored_stock.stock_name == "永泰能源"
    assert len(stored_prices) == len(live_prices)


def test_get_stock_research_payload_rebuilds_prediction_from_recent_window_when_old_prices_are_pathological(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed

    session_factory = build_session_factory()
    session = session_factory()
    session.add(
        StockBasic(
            stock_code="000002",
            stock_name="万科A",
            market="A",
            industry="地产",
            concept_tags=["地产"],
        )
    )

    ancient_dates = [date(1991, 1, 1), date(1991, 1, 2), date(1991, 1, 3)]
    ancient_prices = [-8.8, -9.0, -8.7]
    for trade_date, close_price in zip(ancient_dates, ancient_prices, strict=True):
        session.add(
            DailyPrice(
                stock_code="000002",
                trade_date=trade_date,
                open_price=close_price,
                high_price=close_price,
                low_price=close_price,
                close_price=close_price,
                adj_type="qfq",
                data_source="test",
            )
        )

    recent_anchor = date.today() - timedelta(days=12)
    recent_rows = [
        (0, 10.0, 10.2, 9.8, 10.0),
        (1, 9.8, 9.9, 9.2, 9.4),
        (2, 9.2, 9.3, 8.7, 8.8),
        (3, 8.9, 9.9, 8.9, 9.7),
        (4, 9.8, 10.7, 9.7, 10.6),
        (5, 10.4, 10.5, 9.6, 9.8),
        (6, 9.4, 9.5, 8.8, 8.9),
        (7, 9.1, 10.0, 9.0, 9.9),
        (8, 10.2, 11.0, 10.1, 10.9),
    ]
    for offset, open_price, high_price, low_price, close_price in recent_rows:
        session.add(
            DailyPrice(
                stock_code="000002",
                trade_date=recent_anchor + timedelta(days=offset),
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                adj_type="qfq",
                data_source="test",
            )
        )
    session.commit()

    def fake_fetch_stock_metadata(self, stock_code: str) -> dict[str, object]:
        assert stock_code == "000002"
        return {
            "stock_code": stock_code,
            "stock_name": "万科A",
            "market": "A",
            "industry": "地产",
            "concept_tags": ["地产"],
        }

    def fake_fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, object]]:
        assert stock_code == "000002"
        return [
            {
                "stock_code": stock_code,
                "trade_date": recent_anchor + timedelta(days=offset),
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "close_price": close_price,
                "adj_type": "qfq",
                "volume": 1000,
                "amount": 100000.0,
                "turnover_rate": 1.2,
                "data_source": "akshare",
            }
            for offset, open_price, high_price, low_price, close_price in recent_rows
        ]

    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_stock_metadata", fake_fetch_stock_metadata)
    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_daily_prices", fake_fetch_daily_prices)

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get("/stocks/000002")

    assert response.status_code == 200
    payload = response.json()
    assert payload["stock"]["stock_code"] == "000002"
    assert payload["current_state"]["label"] != "待生成"


def test_get_stock_research_payload_refreshes_today_price_when_stock_already_exists(monkeypatch) -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.stock import StockBasic
    from swinginsight.ingest.adapters.akshare_daily_price_feed import AkshareDailyPriceFeed

    session_factory = build_session_factory()
    session = session_factory()

    stock_code = "000001"
    today = date.today()
    session.add(
        StockBasic(
            stock_code=stock_code,
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=["finance"],
        )
    )
    stale_rows = [
        (today - timedelta(days=8), 10.0, 10.2, 9.8, 10.0),
        (today - timedelta(days=7), 9.8, 9.9, 9.2, 9.4),
        (today - timedelta(days=6), 9.2, 9.3, 8.7, 8.8),
        (today - timedelta(days=5), 8.9, 9.9, 8.9, 9.7),
        (today - timedelta(days=4), 9.8, 10.7, 9.7, 10.6),
        (today - timedelta(days=3), 10.4, 10.5, 9.6, 9.8),
        (today - timedelta(days=2), 9.4, 9.5, 8.8, 8.9),
        (today - timedelta(days=1), 9.1, 10.0, 9.0, 9.9),
        (today, 10.2, 11.0, 10.1, 10.9),
    ]
    for trade_date, open_price, high_price, low_price, close_price in stale_rows:
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=trade_date,
                open_price=open_price,
                high_price=high_price,
                low_price=low_price,
                close_price=close_price,
                adj_type="qfq",
                data_source="test",
            )
        )
    session.commit()

    fetch_calls: list[tuple[str, date | None, date | None]] = []

    def fake_fetch_stock_metadata(self, live_stock_code: str) -> dict[str, object]:
        assert live_stock_code == stock_code
        return {
            "stock_code": live_stock_code,
            "stock_name": "Ping An Bank",
            "market": "A",
            "industry": "Bank",
            "concept_tags": ["finance"],
        }

    def fake_fetch_daily_prices(self, stock_code: str, start: date | None, end: date | None) -> list[dict[str, object]]:
        assert stock_code == "000001"
        fetch_calls.append((stock_code, start, end))
        return [
            {
                "stock_code": stock_code,
                "trade_date": trade_date,
                "open_price": open_price,
                "high_price": high_price,
                "low_price": low_price,
                "close_price": 11.5 if trade_date == today else close_price,
                "adj_type": "qfq",
                "volume": 1000,
                "amount": 100000.0,
                "turnover_rate": 1.2,
                "data_source": "akshare",
            }
            for trade_date, open_price, high_price, low_price, close_price in stale_rows
        ]

    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_stock_metadata", fake_fetch_stock_metadata)
    monkeypatch.setattr(AkshareDailyPriceFeed, "fetch_daily_prices", fake_fetch_daily_prices)

    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.get(f"/stocks/{stock_code}")

    assert response.status_code == 200
    payload = response.json()
    assert fetch_calls
    assert payload["prices"][-1]["trade_date"] == today.isoformat()
    assert payload["prices"][-1]["close_price"] == 11.5


def test_commit_turning_points_persists_logs_and_rebuilds_segments() -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.prediction import PredictionResult
    from swinginsight.db.models.segment import SegmentFeature, SwingSegment
    from swinginsight.db.models.turning_point import PointRevisionLog, TurningPoint

    session_factory = build_session_factory()
    session = session_factory()
    seed_research_data(session)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.post(
        "/stocks/000001/turning-points/commit",
        json={
            "operator": "tester",
            "operations": [
                {
                    "operation_type": "move",
                    "old_value": {"point_date": "2024-01-04", "point_type": "trough", "point_price": 8.8},
                    "new_value": {"point_date": "2024-01-03", "point_type": "trough", "point_price": 9.4},
                },
                {
                    "operation_type": "add",
                    "old_value": None,
                    "new_value": {"point_date": "2024-01-10", "point_type": "trough", "point_price": 8.9},
                },
            ],
            "final_points": [
                {"point_date": "2024-01-03", "point_type": "trough", "point_price": 9.4},
                {"point_date": "2024-01-08", "point_type": "peak", "point_price": 10.6},
                {"point_date": "2024-01-10", "point_type": "trough", "point_price": 8.9},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["rebuild_summary"]["segments"] == 2
    assert payload["rebuild_summary"]["features"] > 0
    assert payload["rebuild_summary"]["predictions"] == 1
    assert len(payload["final_turning_points"]) == 3

    final_points = session.scalars(
        select(TurningPoint).where(TurningPoint.stock_code == "000001", TurningPoint.is_final.is_(True))
    ).all()
    assert len(final_points) == 3
    assert {point.source_type for point in final_points} == {"manual", "system"}

    revision_logs = session.scalars(select(PointRevisionLog)).all()
    assert len(revision_logs) == 2
    assert revision_logs[0].operator == "tester"

    segments = session.scalars(select(SwingSegment).where(SwingSegment.stock_code == "000001")).all()
    assert len(segments) == 2
    features = session.scalars(select(SegmentFeature).where(SegmentFeature.stock_code == "000001")).all()
    assert len(features) > 0
    predictions = session.scalars(select(PredictionResult).where(PredictionResult.stock_code == "000001")).all()
    assert len(predictions) >= 1


def test_commit_turning_points_keeps_unedited_system_points_as_system() -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app
    from swinginsight.db.models.turning_point import TurningPoint

    session_factory = build_session_factory()
    session = session_factory()
    seed_research_data(session)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.post(
        "/stocks/000001/turning-points/commit",
        json={
            "operator": "tester",
            "operations": [],
            "final_points": [
                {"point_date": "2024-01-04", "point_type": "trough", "point_price": 8.8},
                {"point_date": "2024-01-08", "point_type": "peak", "point_price": 10.6},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert {row["source_type"] for row in payload["final_turning_points"]} == {"system"}

    final_points = session.scalars(
        select(TurningPoint).where(TurningPoint.stock_code == "000001", TurningPoint.is_final.is_(True))
    ).all()
    assert {point.source_type for point in final_points} == {"system"}


def test_commit_turning_points_keeps_manual_points_when_they_conflict_with_system_sequence() -> None:
    from fastapi.testclient import TestClient
    from swinginsight.api.main import create_app

    session_factory = build_session_factory()
    session = session_factory()
    seed_research_data(session)
    app = create_app(session_factory=session_factory)
    client = TestClient(app)

    response = client.post(
        "/stocks/000001/turning-points/commit",
        json={
            "operator": "tester",
            "operations": [
                {
                    "operation_type": "add",
                    "old_value": None,
                    "new_value": {"point_date": "2024-01-03", "point_type": "trough", "point_price": 9.2},
                },
                {
                    "operation_type": "add",
                    "old_value": None,
                    "new_value": {"point_date": "2024-01-05", "point_type": "peak", "point_price": 9.9},
                },
            ],
            "final_points": [
                {"point_date": "2024-01-03", "point_type": "trough", "point_price": 9.2},
                {"point_date": "2024-01-04", "point_type": "trough", "point_price": 8.8},
                {"point_date": "2024-01-05", "point_type": "peak", "point_price": 9.9},
                {"point_date": "2024-01-08", "point_type": "peak", "point_price": 10.6},
            ],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert [(row["point_date"], row["point_type"], row["point_price"]) for row in payload["final_turning_points"]] == [
        ("2024-01-03", "trough", 9.2),
        ("2024-01-05", "peak", 9.9),
    ]
