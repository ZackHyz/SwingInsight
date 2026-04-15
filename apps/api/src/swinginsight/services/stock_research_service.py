from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy.exc import IntegrityError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from swinginsight.db.base import Base
from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.pattern import PatternFeature, PatternFutureStat, PatternMatchResult, PatternWindow
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.ingest.daily_price_importer import DailyPriceImporter, ImportResult
from swinginsight.jobs.import_market_data import build_daily_price_feed, ensure_stock_basic
from swinginsight.jobs.import_news import import_news, resolve_news_refresh_window
from swinginsight.jobs.process_news import process_news
from swinginsight.jobs.align_news import align_news
from swinginsight.services.feature_materialization_service import materialize_segment_features
from swinginsight.services.manual_turning_point_service import MANUAL_VERSION_CODE
from swinginsight.services.pattern_feature_service import PatternFeatureService
from swinginsight.services.prediction_service import PredictionService
from swinginsight.services.pattern_window_service import PatternWindowService
from swinginsight.services.segment_generation_service import SegmentGenerationService
from swinginsight.services.turning_point_service import TurningPointService


RESEARCH_LOOKBACK_DAYS = 730
RESEARCH_REFRESH_BUFFER_DAYS = 45
RESEARCH_NEWS_REFRESH_DAYS = 14
REMOTE_REFRESH_STALE_DAYS = 2
MARKET_TIMEZONE = ZoneInfo("Asia/Shanghai")
MARKET_OPEN_TIME = time(9, 15)
MARKET_CLOSE_TIME = time(15, 0)


@dataclass(slots=True, frozen=True)
class NewsRefreshResult:
    start_date: date
    end_date: date
    inserted: int
    processed_count: int
    duplicates: int
    point_mappings: int
    segment_mappings: int


def research_window_start(anchor_date: date | None = None) -> date:
    base_date = anchor_date or date.today()
    return base_date - timedelta(days=RESEARCH_LOOKBACK_DAYS)


def research_refresh_start(latest_trade_date: date | None, anchor_date: date | None = None) -> date:
    base_date = anchor_date or date.today()
    if latest_trade_date is None:
        return research_window_start(base_date)
    return max(research_window_start(base_date), latest_trade_date - timedelta(days=RESEARCH_REFRESH_BUFFER_DAYS))


def current_market_datetime() -> datetime:
    return datetime.now(MARKET_TIMEZONE)


def is_market_session_open(now: datetime | None = None) -> bool:
    current = now or current_market_datetime()
    if current.tzinfo is None:
        current = current.replace(tzinfo=MARKET_TIMEZONE)
    else:
        current = current.astimezone(MARKET_TIMEZONE)
    if current.weekday() >= 5:
        return False
    current_time = current.time()
    return MARKET_OPEN_TIME <= current_time <= MARKET_CLOSE_TIME


def should_refresh_remote_research_data(latest_trade_date: date | None, now: datetime | None = None) -> bool:
    if latest_trade_date is None:
        return True
    current = now or current_market_datetime()
    current_date = current.astimezone(MARKET_TIMEZONE).date() if current.tzinfo is not None else current.date()
    if (current_date - latest_trade_date).days >= REMOTE_REFRESH_STALE_DAYS:
        return True
    return is_market_session_open(current)


class StockResearchService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def ensure_stock_ready(self, stock_code: str) -> bool:
        latest_trade_date_before_refresh = self._load_latest_trade_date(stock_code)
        should_refresh_remote = should_refresh_remote_research_data(latest_trade_date_before_refresh) and not self._has_demo_seed_data(stock_code)
        if should_refresh_remote:
            try:
                import_result = self._refresh_live_prices(stock_code, latest_trade_date=latest_trade_date_before_refresh)
            except IntegrityError:
                self.session.rollback()
                import_result = ImportResult()
        else:
            import_result = ImportResult(skipped=1)
        self.session.commit()
        latest_trade_date = self._load_latest_trade_date(stock_code)
        if latest_trade_date is None:
            return False
        self.session.commit()
        needs_rebuild = self._needs_rebuild(stock_code=stock_code, latest_trade_date=latest_trade_date)
        has_live_price_updates = self._has_live_price_updates(import_result)

        if should_refresh_remote:
            news_refresh = self._refresh_news_window(stock_code=stock_code, anchor_date=latest_trade_date)
            self.session.expire_all()
        else:
            news_refresh = NewsRefreshResult(
                start_date=latest_trade_date,
                end_date=latest_trade_date,
                inserted=0,
                processed_count=0,
                duplicates=0,
                point_mappings=0,
                segment_mappings=0,
            )

        if needs_rebuild or has_live_price_updates:
            self._rebuild_research_artifacts(stock_code=stock_code, latest_trade_date=latest_trade_date)
        elif self._has_news_updates(news_refresh):
            self._refresh_news_features(
                stock_code=stock_code,
                latest_trade_date=latest_trade_date,
                window_start=news_refresh.start_date,
            )

        self._ensure_pattern_similarity_artifacts(
            stock_code=stock_code,
            force_refresh=needs_rebuild or has_live_price_updates,
        )

        self.session.flush()
        return self._stock_exists(stock_code)

    def _refresh_live_prices(self, stock_code: str, *, latest_trade_date: date | None) -> ImportResult:
        feed, source_name = build_daily_price_feed(demo=False)
        ensure_stock_basic(self.session, stock_code)
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

    def _refresh_news_window(self, *, stock_code: str, anchor_date: date) -> NewsRefreshResult:
        window_start, window_end = resolve_news_refresh_window(
            start=anchor_date - timedelta(days=RESEARCH_NEWS_REFRESH_DAYS),
            end=anchor_date,
        )
        for attempt in range(2):
            try:
                inserted = import_news(stock_code=stock_code, start=window_start, end=window_end, session=self.session)
                processing = process_news(stock_code=stock_code, start=window_start, end=window_end, session=self.session)
                alignment = align_news(stock_code=stock_code, start=window_start, end=window_end, session=self.session)
                return NewsRefreshResult(
                    start_date=window_start,
                    end_date=window_end,
                    inserted=inserted,
                    processed_count=processing.processed_count,
                    duplicates=processing.duplicates,
                    point_mappings=alignment.point_mappings,
                    segment_mappings=alignment.segment_mappings,
                )
            except IntegrityError:
                self.session.rollback()
                if attempt == 1:
                    raise

        raise RuntimeError("news refresh retry loop exited unexpectedly")

    def _has_news_updates(self, result: NewsRefreshResult) -> bool:
        return result.inserted > 0 or result.processed_count > 0 or result.point_mappings > 0 or result.segment_mappings > 0

    def _refresh_news_features(self, *, stock_code: str, latest_trade_date: date, window_start: date) -> None:
        overlap_start = window_start - timedelta(days=5)
        segments = self.session.scalars(
            select(SwingSegment)
            .where(
                SwingSegment.stock_code == stock_code,
                SwingSegment.is_final.is_(True),
                SwingSegment.end_date >= overlap_start,
                SwingSegment.start_date <= latest_trade_date,
            )
            .order_by(SwingSegment.end_date.asc(), SwingSegment.id.asc())
        ).all()
        for segment in segments:
            materialize_segment_features(self.session, segment.id)

        if segments:
            self._ensure_pattern_similarity_artifacts(stock_code=stock_code, force_refresh=False)
            PredictionService(self.session).predict(stock_code, latest_trade_date)

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
            self._ensure_pattern_similarity_artifacts(stock_code=stock_code, force_refresh=True)
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

    def _has_demo_seed_data(self, stock_code: str) -> bool:
        return (
            self.session.scalar(
                select(DailyPrice.id)
                .where(DailyPrice.stock_code == stock_code, DailyPrice.data_source == "demo")
                .limit(1)
            )
            is not None
        )

    def _load_latest_trade_date(self, stock_code: str):
        return self.session.scalar(select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_code == stock_code))

    def _ensure_pattern_similarity_artifacts(self, *, stock_code: str, force_refresh: bool) -> None:
        bind = self.session.get_bind()
        Base.metadata.create_all(
            bind=bind,
            tables=[
                PatternWindow.__table__,
                PatternFeature.__table__,
                PatternFutureStat.__table__,
                PatternMatchResult.__table__,
            ],
            checkfirst=True,
        )

        if not force_refresh and not self._pattern_artifacts_missing(stock_code=stock_code):
            return

        pattern_window_service = PatternWindowService(self.session)
        pattern_window_service.build_windows(stock_code=stock_code)
        PatternFeatureService(self.session).materialize(stock_code=stock_code)
        pattern_window_service.materialize_future_stats(stock_code=stock_code)

    def _pattern_artifacts_missing(self, *, stock_code: str) -> bool:
        pattern_window_id = self.session.scalar(
            select(PatternWindow.id).where(PatternWindow.stock_code == stock_code).limit(1)
        )
        if pattern_window_id is None:
            return True

        has_feature = self.session.scalar(
            select(PatternFeature.id)
            .join(PatternWindow, PatternWindow.id == PatternFeature.window_id)
            .where(PatternWindow.stock_code == stock_code)
            .limit(1)
        )
        if has_feature is None:
            return True

        has_future_stat = self.session.scalar(
            select(PatternFutureStat.id)
            .join(PatternWindow, PatternWindow.id == PatternFutureStat.window_id)
            .where(PatternWindow.stock_code == stock_code)
            .limit(1)
        )
        return has_future_stat is None
