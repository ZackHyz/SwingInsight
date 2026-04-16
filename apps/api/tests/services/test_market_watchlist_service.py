from __future__ import annotations

from datetime import date, datetime, timedelta
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


def seed_scan_inputs(session) -> None:
    from swinginsight.db.models.market_data import DailyPrice
    from swinginsight.db.models.news import NewsRaw
    from swinginsight.db.models.prediction import PredictionResult
    from swinginsight.db.models.stock import StockBasic

    session.add_all(
        [
            StockBasic(stock_code="000001", stock_name="Ping An Bank", market="A", industry="Bank", concept_tags=["finance"]),
            StockBasic(stock_code="600157", stock_name="Yongtai Energy", market="A", industry="Coal", concept_tags=["energy"]),
        ]
    )

    for stock_code in ["000001", "600157"]:
        session.add(
            DailyPrice(
                stock_code=stock_code,
                trade_date=date(2026, 4, 16),
                open_price=10.0,
                high_price=10.3,
                low_price=9.8,
                close_price=10.1,
                adj_type="qfq",
                data_source="test",
            )
        )

    session.add_all(
        [
            PredictionResult(
                stock_code="000001",
                predict_date=date(2026, 4, 16),
                current_state="up",
                up_prob_5d=0.6,
                flat_prob_5d=0.2,
                down_prob_5d=0.2,
                up_prob_10d=0.66,
                flat_prob_10d=0.2,
                down_prob_10d=0.14,
                up_prob_20d=0.58,
                flat_prob_20d=0.22,
                down_prob_20d=0.2,
                similarity_topn_json=[{"id": 1}, {"id": 2}, {"id": 3}, {"id": 4}],
                key_features_json={},
                risk_flags_json={},
                model_version="prediction:v1",
                summary="s1",
            ),
            PredictionResult(
                stock_code="600157",
                predict_date=date(2026, 4, 16),
                current_state="flat",
                up_prob_5d=0.48,
                flat_prob_5d=0.3,
                down_prob_5d=0.22,
                up_prob_10d=0.44,
                flat_prob_10d=0.33,
                down_prob_10d=0.23,
                up_prob_20d=0.42,
                flat_prob_20d=0.36,
                down_prob_20d=0.22,
                similarity_topn_json=[{"id": 9}],
                key_features_json={},
                risk_flags_json={},
                model_version="prediction:v1",
                summary="s2",
            ),
        ]
    )

    for idx in range(3):
        session.add(
            NewsRaw(
                news_uid=f"n-{idx}",
                stock_code="000001",
                title=f"000001 news {idx}",
                summary=None,
                content=None,
                publish_time=datetime(2026, 4, 16, 9, 0),
                news_date=date(2026, 4, 16) - timedelta(days=idx),
                source_name="test",
                source_type="news",
                url=f"https://example.com/{idx}",
                data_source="test",
            )
        )
    session.commit()


def test_run_market_scan_persists_ranked_watchlist_rows() -> None:
    from swinginsight.db.models.watchlist import MarketScanResult
    from swinginsight.services.market_watchlist_service import MarketWatchlistService

    session = build_session()
    seed_scan_inputs(session)

    summary = MarketWatchlistService(session).run_scan(scan_date=date(2026, 4, 16))

    rows = session.scalars(
        select(MarketScanResult).where(MarketScanResult.scan_date == date(2026, 4, 16)).order_by(MarketScanResult.rank_no.asc())
    ).all()

    assert summary["scan_date"] == "2026-04-16"
    assert summary["rows"] == 2
    assert rows[0].stock_code == "000001"
    assert rows[0].rank_no == 1
    assert rows[0].sample_count >= rows[1].sample_count
