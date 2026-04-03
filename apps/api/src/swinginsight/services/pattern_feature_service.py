from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.pattern import PatternFeature, PatternWindow
from swinginsight.domain.prediction.pattern_features import build_pattern_features


@dataclass(slots=True, frozen=True)
class PatternFeatureMaterializeResult:
    windows: int
    features: int
    skipped: int


class PatternFeatureService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def materialize(self, *, stock_code: str) -> PatternFeatureMaterializeResult:
        windows = self.session.scalars(
            select(PatternWindow)
            .where(PatternWindow.stock_code == stock_code)
            .order_by(PatternWindow.end_date.asc(), PatternWindow.id.asc())
        ).all()
        created_or_updated = 0
        skipped = 0
        for window in windows:
            history_rows = self.session.scalars(
                select(DailyPrice)
                .where(DailyPrice.stock_code == stock_code, DailyPrice.trade_date <= window.end_date)
                .order_by(DailyPrice.trade_date.asc())
            ).all()
            window_rows = [row for row in history_rows if window.start_date <= row.trade_date <= window.end_date]
            payload = build_pattern_features(window_rows=window_rows, history_rows=history_rows)
            if payload is None:
                skipped += 1
                continue

            row = self.session.scalar(select(PatternFeature).where(PatternFeature.window_id == window.id))
            values = {
                "price_seq_json": payload["price_seq"],
                "return_seq_json": payload["return_seq"],
                "candle_feat_json": payload["candle_feat"],
                "volume_seq_json": payload["volume_seq"],
                "turnover_seq_json": payload["turnover_seq"],
                "trend_context_json": payload["trend_context"],
                "vola_context_json": payload["vola_context"],
                "coarse_vector_json": payload["coarse_vector"],
                "feature_version": window.feature_version or "pattern:v1",
            }
            if row is None:
                self.session.add(PatternFeature(window_id=window.id, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            created_or_updated += 1

        self.session.flush()
        return PatternFeatureMaterializeResult(windows=len(windows), features=created_or_updated, skipped=skipped)
