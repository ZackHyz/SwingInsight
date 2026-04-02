from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.ingest.daily_price_importer import DailyPriceImporter, ImportResult
from swinginsight.jobs.import_market_data import build_daily_price_feed, ensure_stock_basic
from swinginsight.services.feature_materialization_service import materialize_segment_features
from swinginsight.services.manual_turning_point_service import MANUAL_VERSION_CODE
from swinginsight.services.prediction_service import PredictionService
from swinginsight.services.segment_generation_service import SegmentGenerationService
from swinginsight.services.turning_point_service import TurningPointService


RESEARCH_LOOKBACK_DAYS = 730
RESEARCH_REFRESH_BUFFER_DAYS = 45


def research_window_start(anchor_date: date | None = None) -> date:
    base_date = anchor_date or date.today()
    return base_date - timedelta(days=RESEARCH_LOOKBACK_DAYS)


def research_refresh_start(latest_trade_date: date | None, anchor_date: date | None = None) -> date:
    base_date = anchor_date or date.today()
    if latest_trade_date is None:
        return research_window_start(base_date)
    return max(research_window_start(base_date), latest_trade_date - timedelta(days=RESEARCH_REFRESH_BUFFER_DAYS))


class StockResearchService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_stock_ready(self, stock_code: str) -> bool:
        latest_trade_date_before_refresh = self._load_latest_trade_date(stock_code)
        import_result = self._refresh_live_prices(stock_code, latest_trade_date=latest_trade_date_before_refresh)
        latest_trade_date = self._load_latest_trade_date(stock_code)
        if latest_trade_date is None:
            return False

        if self._needs_rebuild(stock_code=stock_code, latest_trade_date=latest_trade_date) or self._has_live_price_updates(import_result):
            self._rebuild_research_artifacts(stock_code=stock_code, latest_trade_date=latest_trade_date)

        self.session.flush()
        return self._stock_exists(stock_code)

    def _refresh_live_prices(self, stock_code: str, *, latest_trade_date: date | None) -> ImportResult:
        feed, source_name = build_daily_price_feed(demo=False)
        ensure_stock_basic(self.session, stock_code, feed)
        return DailyPriceImporter(session=self.session, feed=feed, source_name=source_name).run(
            stock_code=stock_code,
            start=research_refresh_start(latest_trade_date),
        )

    def _needs_rebuild(self, *, stock_code: str, latest_trade_date) -> bool:
        has_final_points = self.session.scalar(
            select(TurningPoint.id)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
            .limit(1)
        )
        has_final_segments = self.session.scalar(
            select(SwingSegment.id)
            .where(SwingSegment.stock_code == stock_code, SwingSegment.is_final.is_(True))
            .limit(1)
        )
        has_prediction = self.session.scalar(
            select(PredictionResult.id)
            .where(PredictionResult.stock_code == stock_code, PredictionResult.predict_date == latest_trade_date)
            .limit(1)
        )
        return not (has_final_points and has_final_segments and has_prediction)

    def _has_live_price_updates(self, import_result: ImportResult) -> bool:
        return import_result.inserted > 0 or import_result.updated > 0

    def _rebuild_research_artifacts(self, *, stock_code: str, latest_trade_date) -> None:
        turning_point_result = TurningPointService(self.session).rebuild_points(
            stock_code=stock_code,
            algo="zigzag",
            start_date=research_window_start(latest_trade_date),
        )
        version_code = self._resolve_segment_version_code(stock_code=stock_code, fallback_version=turning_point_result.version_code)
        SegmentGenerationService(self.session).rebuild_segments(stock_code=stock_code, version_code=version_code)

        rebuilt_segments = self.session.scalars(
            select(SwingSegment)
            .where(
                SwingSegment.stock_code == stock_code,
                SwingSegment.source_version == version_code,
                SwingSegment.is_final.is_(True),
            )
            .order_by(SwingSegment.end_date.asc(), SwingSegment.id.asc())
        ).all()
        for segment in rebuilt_segments:
            materialize_segment_features(self.session, segment.id)

        if rebuilt_segments:
            PredictionService(self.session).predict(stock_code, latest_trade_date)

    def _resolve_segment_version_code(self, *, stock_code: str, fallback_version: str) -> str:
        has_manual_points = self.session.scalar(
            select(TurningPoint.id)
            .where(
                TurningPoint.stock_code == stock_code,
                TurningPoint.source_type == "manual",
                TurningPoint.version_code == MANUAL_VERSION_CODE,
                TurningPoint.is_final.is_(True),
            )
            .limit(1)
        )
        if has_manual_points:
            return MANUAL_VERSION_CODE
        return fallback_version

    def _stock_exists(self, stock_code: str) -> bool:
        stock = self.session.scalar(select(StockBasic.id).where(StockBasic.stock_code == stock_code).limit(1))
        return stock is not None

    def _load_latest_trade_date(self, stock_code: str):
        return self.session.scalar(select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_code == stock_code))
