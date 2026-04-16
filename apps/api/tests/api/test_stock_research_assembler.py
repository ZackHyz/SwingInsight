from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
import sys
from types import SimpleNamespace


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_build_stock_research_payload_formats_existing_contract(monkeypatch) -> None:
    from swinginsight.api.assemblers import stock_research_assembler as assembler
    from swinginsight.api.readers.stock_research_reader import StockResearchNewsRow, StockResearchSnapshot

    monkeypatch.setattr(assembler, "resolve_base_sentiment_score", lambda *_args, **_kwargs: 0.0)
    monkeypatch.setattr(assembler, "resolve_heat_score", lambda *_args, **_kwargs: 0.0)
    monkeypatch.setattr(
        assembler,
        "adjust_sentiment_with_position",
        lambda **kwargs: 0.8 if kwargs.get("point_type") == "peak" else -0.6,
    )

    snapshot = StockResearchSnapshot(
        stock=SimpleNamespace(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=["finance", "bluechip"],
        ),
        prices=[
            SimpleNamespace(
                trade_date=date(2024, 1, 2),
                open_price=Decimal("10.0"),
                high_price=Decimal("10.2"),
                low_price=Decimal("9.8"),
                close_price=Decimal("10.1"),
                volume=1000,
            )
        ],
        auto_points=[
            SimpleNamespace(
                id=10,
                point_date=date(2024, 1, 3),
                point_type="trough",
                point_price=Decimal("9.4"),
                source_type="system",
            )
        ],
        final_points=[
            SimpleNamespace(
                id=20,
                point_date=date(2024, 1, 8),
                point_type="peak",
                point_price=Decimal("10.6"),
                source_type="manual",
            )
        ],
        trade_markers=[
            SimpleNamespace(
                id=30,
                trade_date=date(2024, 1, 9),
                trade_type="buy",
                price=Decimal("9.8"),
                quantity=100,
                strategy_tag="swing",
                note="starter",
            )
        ],
        news_rows=[
            StockResearchNewsRow(
                raw=SimpleNamespace(
                    id=1,
                    title="Liquidity support boosts banks",
                    summary="Policy support",
                    source_name="Exchange",
                    source_type="test",
                    news_date=date(2024, 1, 7),
                    sentiment="neutral",
                ),
                processed=SimpleNamespace(
                    category="announcement",
                    sub_category="earnings",
                    sentiment="positive",
                    heat_level="high",
                ),
                sentiment_result=SimpleNamespace(
                    sentiment_score_base=0.4,
                    heat_score=0.9,
                    sentiment_label="positive",
                    event_conflict_flag=False,
                ),
                segment_mapping=SimpleNamespace(relation_type="inside_segment", distance_days=0),
                point_mapping=SimpleNamespace(point_type="peak", relation_type="before_point", distance_days=-2),
                event_metadata={
                    "event_types": ["earnings"],
                    "positive_event_count": 1,
                    "negative_event_count": 0,
                },
            ),
            StockResearchNewsRow(
                raw=SimpleNamespace(
                    id=2,
                    title="Major shareholder plans reduction",
                    summary="Placement plan",
                    source_name="Exchange",
                    source_type="announcement",
                    news_date=date(2024, 1, 6),
                    sentiment="negative",
                ),
                processed=SimpleNamespace(
                    category=None,
                    sub_category="capital_action",
                    sentiment="negative",
                    heat_level="low",
                ),
                sentiment_result=SimpleNamespace(
                    sentiment_score_base=-0.5,
                    heat_score=0.2,
                    sentiment_label=None,
                    event_conflict_flag=True,
                ),
                segment_mapping=SimpleNamespace(relation_type="before_start", distance_days=-1),
                point_mapping=None,
                event_metadata={
                    "event_types": ["capital_action", "governance"],
                    "positive_event_count": 0,
                    "negative_event_count": 2,
                },
            ),
        ],
        prediction={
            "label": "观察",
            "summary": "已有预测",
            "probabilities": {"up": 0.6},
            "key_features": {"pattern_score": 0.7},
            "risk_flags": {"news": "watch"},
            "similar_cases": [],
        },
    )

    payload = assembler.build_stock_research_payload(snapshot)

    assert payload["stock"] == {
        "stock_code": "000001",
        "stock_name": "Ping An Bank",
        "market": "A",
        "industry": "Bank",
        "concept_tags": ["finance", "bluechip"],
    }
    assert payload["prices"] == [
        {
            "trade_date": "2024-01-02",
            "open_price": 10.0,
            "high_price": 10.2,
            "low_price": 9.8,
            "close_price": 10.1,
            "volume": 1000,
        }
    ]
    assert payload["auto_turning_points"][0]["source_type"] == "system"
    assert payload["final_turning_points"][0]["source_type"] == "manual"
    assert payload["trade_markers"][0]["trade_type"] == "buy"

    assert len(payload["news_items"]) == 2
    assert payload["news_items"][0] == {
        "news_id": 1,
        "title": "Liquidity support boosts banks",
        "summary": "Policy support",
        "source_name": "Exchange",
        "source_type": "test",
        "news_date": "2024-01-07",
        "category": "announcement",
        "sub_category": "earnings",
        "sentiment": "positive",
        "display_tags": ["当前波段内", "顶部前2日", "公告", "利多"],
        "sentiment_score_adjusted": 0.8,
        "event_types": ["earnings"],
        "event_conflict_flag": False,
    }
    assert payload["news_items"][1]["display_tags"] == ["波段起点前1日", "公告", "利空"]
    assert payload["news_items"][1]["event_types"] == ["capital_action", "governance"]
    assert payload["news_items"][1]["event_conflict_flag"] is True

    assert payload["current_state"]["label"] == "观察"
    assert payload["current_state"]["probabilities"] == {"up": 0.6}
    assert payload["current_state"]["news_summary"] == {
        "window_news_count": 2.0,
        "announcement_count": 2.0,
        "positive_news_ratio": 0.5,
        "high_heat_count": 1.0,
        "avg_adjusted_sentiment": 0.1,
        "positive_event_count": 1.0,
        "negative_event_count": 2.0,
        "governance_event_count": 1.0,
    }


def test_build_stock_research_payload_returns_zeroed_news_summary_without_news() -> None:
    from swinginsight.api.assemblers.stock_research_assembler import build_stock_research_payload
    from swinginsight.api.readers.stock_research_reader import StockResearchSnapshot

    snapshot = StockResearchSnapshot(
        stock=SimpleNamespace(
            stock_code="000001",
            stock_name="Ping An Bank",
            market="A",
            industry="Bank",
            concept_tags=None,
        ),
        prices=[],
        auto_points=[],
        final_points=[],
        trade_markers=[],
        news_rows=[],
        prediction=None,
    )

    payload = build_stock_research_payload(snapshot)

    assert payload["stock"]["concept_tags"] == []
    assert payload["news_items"] == []
    assert payload["current_state"] == {
        "label": "待生成",
        "summary": "预测结果待生成",
        "probabilities": {},
        "key_features": {},
        "risk_flags": {},
        "similar_cases": [],
        "news_summary": {
            "window_news_count": 0.0,
            "announcement_count": 0.0,
            "positive_news_ratio": 0.0,
            "high_heat_count": 0.0,
            "avg_adjusted_sentiment": 0.0,
            "positive_event_count": 0.0,
            "negative_event_count": 0.0,
            "governance_event_count": 0.0,
        },
    }
