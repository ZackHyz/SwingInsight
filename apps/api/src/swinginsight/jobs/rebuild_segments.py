from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.ingest.daily_price_importer import DailyPriceImporter
from swinginsight.services.segment_generation_service import SegmentGenerationService
from swinginsight.services.turning_point_service import TurningPointService


class RebuildSegmentsDemoFeed:
    def fetch_daily_prices(self, stock_code: str, start: date | None = None, end: date | None = None):
        return [
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 2),
                "open_price": 10.0,
                "high_price": 10.2,
                "low_price": 9.8,
                "close_price": 10.0,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 3),
                "open_price": 9.8,
                "high_price": 9.9,
                "low_price": 9.2,
                "close_price": 9.4,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 4),
                "open_price": 9.2,
                "high_price": 9.3,
                "low_price": 8.7,
                "close_price": 8.8,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 5),
                "open_price": 8.9,
                "high_price": 9.9,
                "low_price": 8.9,
                "close_price": 9.7,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 8),
                "open_price": 9.8,
                "high_price": 10.7,
                "low_price": 9.7,
                "close_price": 10.6,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 9),
                "open_price": 10.4,
                "high_price": 10.5,
                "low_price": 9.6,
                "close_price": 9.8,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 10),
                "open_price": 9.4,
                "high_price": 9.5,
                "low_price": 8.8,
                "close_price": 8.9,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 11),
                "open_price": 9.1,
                "high_price": 10.0,
                "low_price": 9.0,
                "close_price": 9.9,
                "adj_type": "qfq",
                "data_source": "demo",
            },
            {
                "stock_code": stock_code,
                "trade_date": date(2024, 1, 12),
                "open_price": 10.2,
                "high_price": 11.0,
                "low_price": 10.1,
                "close_price": 10.9,
                "adj_type": "qfq",
                "data_source": "demo",
            },
        ]


@dataclass(slots=True, frozen=True)
class RebuildSegmentsResult:
    turning_points: int
    segments: int
    version_code: str


def rebuild_segments(
    *,
    stock_code: str,
    algo: str,
    demo: bool = False,
    reversal_pct: float = 0.08,
    min_separation_pct: float = 0.05,
) -> RebuildSegmentsResult:
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        if demo:
            importer = DailyPriceImporter(session=session, feed=RebuildSegmentsDemoFeed(), source_name="demo")
            importer.run(stock_code=stock_code)

        turning_point_result = TurningPointService(session).rebuild_points(
            stock_code=stock_code,
            algo=algo,
            reversal_pct=reversal_pct,
            min_separation_pct=min_separation_pct,
        )
        segment_result = SegmentGenerationService(session).rebuild_segments(
            stock_code=stock_code,
            version_code=turning_point_result.version_code,
        )
        return RebuildSegmentsResult(
            turning_points=turning_point_result.inserted,
            segments=segment_result.inserted,
            version_code=turning_point_result.version_code,
        )
