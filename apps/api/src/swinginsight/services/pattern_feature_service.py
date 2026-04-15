from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.pattern import PatternFeature, PatternWindow
from swinginsight.domain.prediction.pattern_features import build_pattern_features
from swinginsight.services.feature_engineering import (
    compute_price_position_features,
    compute_trend_context_features,
    compute_volume_context_features,
)


@dataclass(slots=True, frozen=True)
class PatternFeatureMaterializeResult:
    windows: int
    features: int
    skipped: int


class PatternFeatureService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def materialize(self, *, stock_code: str, feature_sets: list[str] | None = None) -> PatternFeatureMaterializeResult:
        target_sets = set(feature_sets or ["coarse"])
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
            pre_rows = [row for row in history_rows if row.trade_date < window.start_date]
            coarse_payload = build_pattern_features(window_rows=window_rows, history_rows=history_rows) if "coarse" in target_sets else None
            context_payload = self._build_context_payload(
                target_sets=target_sets,
                window_rows=window_rows,
                history_rows=history_rows,
                pre_rows=pre_rows,
            )
            if coarse_payload is None and not context_payload and "coarse" in target_sets:
                skipped += 1
                continue

            row = self.session.scalar(select(PatternFeature).where(PatternFeature.window_id == window.id))
            values: dict[str, object] = {
                "feature_version": window.feature_version or "pattern:v1",
            }
            if coarse_payload is not None:
                values |= {
                    "price_seq_json": coarse_payload["price_seq"],
                    "return_seq_json": coarse_payload["return_seq"],
                    "candle_feat_json": coarse_payload["candle_feat"],
                    "volume_seq_json": coarse_payload["volume_seq"],
                    "turnover_seq_json": coarse_payload["turnover_seq"],
                    "trend_context_json": coarse_payload["trend_context"],
                    "vola_context_json": coarse_payload["vola_context"],
                    "coarse_vector_json": coarse_payload["coarse_vector"],
                }
            if context_payload:
                merged_context = {
                    **((row.context_feature_json if row is not None and row.context_feature_json else {})),
                    **context_payload,
                }
                values["context_feature_json"] = merged_context

            if row is None:
                self.session.add(PatternFeature(window_id=window.id, **values))
            else:
                for key, value in values.items():
                    setattr(row, key, value)
            created_or_updated += 1

        self.session.flush()
        return PatternFeatureMaterializeResult(windows=len(windows), features=created_or_updated, skipped=skipped)

    def _build_context_payload(
        self,
        *,
        target_sets: set[str],
        window_rows: list[DailyPrice],
        history_rows: list[DailyPrice],
        pre_rows: list[DailyPrice],
    ) -> dict[str, float]:
        payload: dict[str, float] = {}
        if "volume_context" in target_sets:
            payload |= compute_volume_context_features(window_rows=window_rows, pre_rows=pre_rows)
        if "price_position" in target_sets:
            payload |= compute_price_position_features(history_rows=history_rows)
        if "trend_context" in target_sets:
            payload |= compute_trend_context_features(pre_rows=pre_rows)
        return payload
