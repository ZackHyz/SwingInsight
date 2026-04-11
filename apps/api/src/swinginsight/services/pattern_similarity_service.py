from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import mean, median

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.pattern import PatternFeature, PatternFutureStat, PatternWindow
from swinginsight.db.models.segment import SwingSegment
from swinginsight.domain.prediction.pattern_similarity import calc_pattern_similarity, sim_candle, sim_price
from swinginsight.services.prediction_service import SimilarCase


@dataclass(slots=True, frozen=True)
class PatternSearchResult:
    similar_cases: list[SimilarCase]
    group_stat: dict[str, float]
    query_window: dict[str, object] | None


class PatternSimilarityService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def select_representative_window(self, current_segment: SwingSegment) -> PatternWindow | None:
        windows = self.session.scalars(
            select(PatternWindow)
            .where(PatternWindow.segment_id == current_segment.id)
            .order_by(PatternWindow.start_date.asc(), PatternWindow.id.asc())
        ).all()
        if not windows:
            return None

        midpoint = current_segment.start_date + (current_segment.end_date - current_segment.start_date) / 2
        features_by_window_id = self._features_by_window_id([window.id for window in windows])
        segment_price_rows = self.session.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_code == current_segment.stock_code,
                DailyPrice.trade_date >= current_segment.start_date,
                DailyPrice.trade_date <= current_segment.end_date,
            )
            .order_by(DailyPrice.trade_date.asc(), DailyPrice.id.asc())
        ).all()
        segment_closes = [float(row.close_price) for row in segment_price_rows if row.close_price is not None]
        max_date_gap = max(
            abs(((window.start_date + (window.end_date - window.start_date) / 2) - midpoint).days) for window in windows
        )
        prototype = self._build_segment_candle_prototype(windows, features_by_window_id, segment_closes)

        def priority(window: PatternWindow) -> tuple[float, int, float, int]:
            center = window.start_date + (window.end_date - window.start_date) / 2
            date_gap = abs((center - midpoint).days)
            pct_gap = abs(float(window.period_pct_change or 0) - float(current_segment.pct_change or 0))
            representative_score = self._representative_score(
                window=window,
                feature_row=features_by_window_id.get(window.id),
                segment_closes=segment_closes,
                segment_prototype=prototype,
                date_gap=date_gap,
                max_date_gap=max_date_gap,
                segment_pct_change=float(current_segment.pct_change or 0),
            )
            return (-representative_score, date_gap, pct_gap, window.id)

        return sorted(windows, key=priority)[0]

    def find_similar_windows(self, *, current_segment: SwingSegment, top_n: int = 300, top_k: int = 5) -> PatternSearchResult:
        query_window = self.select_representative_window(current_segment)
        if query_window is None:
            return PatternSearchResult(similar_cases=[], group_stat=self._empty_group_stat(), query_window=None)

        query_feature_row = self.session.scalar(select(PatternFeature).where(PatternFeature.window_id == query_window.id))
        if query_feature_row is None:
            return PatternSearchResult(similar_cases=[], group_stat=self._empty_group_stat(), query_window=None)
        query_features = self._feature_payload(query_feature_row)

        candidates = self.session.scalars(
            select(PatternWindow)
            .where(PatternWindow.id != query_window.id)
            .where(PatternWindow.end_date < query_window.start_date)
            .order_by(PatternWindow.end_date.asc(), PatternWindow.id.asc())
        ).all()
        ranked_candidates: list[tuple[float, PatternWindow, PatternFeature]] = []
        for candidate in candidates:
            feature_row = self.session.scalar(select(PatternFeature).where(PatternFeature.window_id == candidate.id))
            if feature_row is None:
                continue
            ranked_candidates.append((self._coarse_similarity(query_feature_row, feature_row), candidate, feature_row))

        ranked_candidates.sort(key=lambda item: item[0], reverse=True)
        shortlist = ranked_candidates[:top_n]
        cases: list[SimilarCase] = []
        for _, candidate, feature_row in shortlist:
            candidate_features = self._feature_payload(feature_row)
            scores = calc_pattern_similarity(query_features, candidate_features)
            segment = None
            if candidate.segment_id is not None:
                segment = self.session.scalar(select(SwingSegment).where(SwingSegment.id == candidate.segment_id))
            future_stat = self.session.scalar(select(PatternFutureStat).where(PatternFutureStat.window_id == candidate.id))
            forward_returns = {
                1: float(future_stat.ret_1d) if future_stat and future_stat.ret_1d is not None else None,
                3: float(future_stat.ret_3d) if future_stat and future_stat.ret_3d is not None else None,
                5: float(future_stat.ret_5d) if future_stat and future_stat.ret_5d is not None else None,
                10: float(future_stat.ret_10d) if future_stat and future_stat.ret_10d is not None else None,
                20: None,
            }
            cases.append(
                SimilarCase(
                    segment_id=segment.id if segment is not None else int(candidate.segment_id or -1),
                    stock_code=candidate.stock_code,
                    score=scores["total_similarity"],
                    price_score=scores["sim_price"],
                    volume_score=scores["sim_volume"],
                    turnover_score=scores["sim_turnover"],
                    pattern_score=scores["sim_candle"],
                    pct_change=float(segment.pct_change) if segment and segment.pct_change is not None else float(candidate.period_pct_change or 0),
                    start_date=segment.start_date if segment is not None else candidate.start_date,
                    end_date=segment.end_date if segment is not None else candidate.end_date,
                    forward_returns=forward_returns,
                    window_id=candidate.id,
                    window_start_date=candidate.start_date,
                    window_end_date=candidate.end_date,
                    window_size=candidate.window_size,
                    segment_start_date=segment.start_date if segment is not None else None,
                    segment_end_date=segment.end_date if segment is not None else None,
                    candle_score=scores["sim_candle"],
                    trend_score=scores["sim_trend"],
                    vola_score=scores["sim_vola"],
                )
            )

        cases.sort(
            key=lambda case: (
                0 if case.stock_code == current_segment.stock_code else 1,
                -case.score,
                case.window_end_date or case.end_date,
                case.window_id or 0,
            )
        )
        top_cases = cases[:top_k]
        return PatternSearchResult(
            similar_cases=top_cases,
            group_stat=self._summarize_future_returns(top_cases),
            query_window={
                "window_id": query_window.id,
                "start_date": query_window.start_date,
                "end_date": query_window.end_date,
                "window_size": query_window.window_size,
                "segment_id": current_segment.id,
            },
        )

    def _feature_payload(self, row: PatternFeature) -> dict[str, object]:
        price_seq = list(row.price_seq_json or [])
        candle_feat = list(row.candle_feat_json or [])
        return {
            "price_seq": price_seq,
            "candle_feat": candle_feat,
            "bull_flags": [int(candle_feat[index]) for index in range(4, len(candle_feat), 5)],
            "highest_day_pos": price_seq.index(max(price_seq)) if price_seq else 0,
            "lowest_day_pos": price_seq.index(min(price_seq)) if price_seq else 0,
            "volume_seq": list(row.volume_seq_json or []),
            "turnover_seq": list(row.turnover_seq_json or []),
            "trend_context": list(row.trend_context_json or []),
            "vola_context": list(row.vola_context_json or []),
            "coarse_vector": list(row.coarse_vector_json or []),
        }

    def _coarse_similarity(self, left: PatternFeature, right: PatternFeature) -> float:
        vector_left = list(left.coarse_vector_json or [])
        vector_right = list(right.coarse_vector_json or [])
        size = min(len(vector_left), len(vector_right))
        if size == 0:
            return 0.0
        left_slice = vector_left[:size]
        right_slice = vector_right[:size]
        numerator = sum(a * b for a, b in zip(left_slice, right_slice, strict=False))
        left_norm = sum(a * a for a in left_slice) ** 0.5
        right_norm = sum(b * b for b in right_slice) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return (numerator / (left_norm * right_norm) + 1.0) / 2.0

    def _features_by_window_id(self, window_ids: list[int]) -> dict[int, PatternFeature]:
        if not window_ids:
            return {}
        return {
            row.window_id: row
            for row in self.session.scalars(select(PatternFeature).where(PatternFeature.window_id.in_(window_ids))).all()
        }

    def _representative_score(
        self,
        *,
        window: PatternWindow,
        feature_row: PatternFeature | None,
        segment_closes: list[float],
        segment_prototype: dict[str, object] | None,
        date_gap: int,
        max_date_gap: int,
        segment_pct_change: float,
    ) -> float:
        pct_gap = abs(float(window.period_pct_change or 0) - segment_pct_change)
        midpoint_score = 1.0 if max_date_gap == 0 else max(0.0, 1.0 - (date_gap / max_date_gap))
        amplitude_score = self._amplitude_coverage(float(window.period_pct_change or 0), segment_pct_change)
        if feature_row is None or not segment_closes or segment_prototype is None:
            return round(0.7 * midpoint_score + 0.3 * max(0.0, 1.0 - pct_gap / 100.0), 4)

        feature_payload = self._feature_payload(feature_row)
        target_price_seq = self._normalize_trajectory(
            self._resample_series(segment_closes, len(feature_payload["price_seq"]))
        )
        price_score = sim_price(self._normalize_trajectory(feature_payload["price_seq"]), target_price_seq)
        candle_score = sim_candle(feature_payload, segment_prototype)
        return round(
            0.45 * price_score + 0.25 * candle_score + 0.2 * midpoint_score + 0.1 * amplitude_score,
            4,
        )

    def _build_segment_candle_prototype(
        self,
        windows: list[PatternWindow],
        features_by_window_id: dict[int, PatternFeature],
        segment_closes: list[float],
    ) -> dict[str, object] | None:
        candle_vectors = [
            list(feature_row.candle_feat_json or [])
            for window in windows
            if (feature_row := features_by_window_id.get(window.id)) is not None and feature_row.candle_feat_json
        ]
        if not candle_vectors or not segment_closes:
            return None

        size = min(len(vector) for vector in candle_vectors)
        averaged = [
            sum(float(vector[index]) for vector in candle_vectors) / len(candle_vectors)
            for index in range(size)
        ]
        bull_flags = [1 if averaged[index] >= 0.5 else 0 for index in range(4, size, 5)]
        resampled = self._resample_series(segment_closes, max(len(bull_flags), 1))
        highest_day_pos = resampled.index(max(resampled)) if resampled else 0
        lowest_day_pos = resampled.index(min(resampled)) if resampled else 0
        return {
            "candle_feat": averaged,
            "bull_flags": bull_flags,
            "highest_day_pos": highest_day_pos,
            "lowest_day_pos": lowest_day_pos,
        }

    def _resample_series(self, values: list[float], target_size: int) -> list[float]:
        if not values or target_size <= 0:
            return []
        if len(values) == target_size:
            return [float(value) for value in values]
        if target_size == 1:
            return [float(values[0])]
        step = (len(values) - 1) / (target_size - 1)
        resampled: list[float] = []
        for index in range(target_size):
            position = index * step
            left = int(position)
            right = min(left + 1, len(values) - 1)
            if left == right:
                resampled.append(float(values[left]))
                continue
            fraction = position - left
            interpolated = float(values[left]) + (float(values[right]) - float(values[left])) * fraction
            resampled.append(interpolated)
        return resampled

    def _amplitude_coverage(self, window_pct_change: float, segment_pct_change: float) -> float:
        denominator = abs(segment_pct_change)
        if denominator == 0:
            return 1.0 if abs(window_pct_change) == 0 else 0.0
        return max(0.0, min(1.0, abs(window_pct_change) / denominator))

    def _normalize_trajectory(self, values: list[float]) -> list[float]:
        if not values:
            return []
        baseline = float(values[0])
        if baseline == 0:
            return [float(value) for value in values]
        return [round((float(value) / baseline) - 1.0, 6) for value in values]

    def _summarize_future_returns(self, cases: list[SimilarCase]) -> dict[str, float]:
        return {
            "sample_count": float(len(cases)),
            "future_1d_mean": self._mean([case.forward_returns.get(1) for case in cases]),
            "future_1d_median": self._median([case.forward_returns.get(1) for case in cases]),
            "future_1d_win_rate": self._win_rate([case.forward_returns.get(1) for case in cases]),
            "future_3d_mean": self._mean([case.forward_returns.get(3) for case in cases]),
            "future_5d_mean": self._mean([case.forward_returns.get(5) for case in cases]),
            "future_10d_mean": self._mean([case.forward_returns.get(10) for case in cases]),
            "future_5d_max_dd_median": 0.0,
            "future_10d_max_dd_median": 0.0,
        }

    def _empty_group_stat(self) -> dict[str, float]:
        return {
            "sample_count": 0.0,
            "future_1d_mean": 0.0,
            "future_1d_median": 0.0,
            "future_1d_win_rate": 0.0,
            "future_3d_mean": 0.0,
            "future_5d_mean": 0.0,
            "future_10d_mean": 0.0,
            "future_5d_max_dd_median": 0.0,
            "future_10d_max_dd_median": 0.0,
        }

    def _mean(self, values: list[float | None]) -> float:
        cleaned = [float(value) for value in values if value is not None]
        return round(mean(cleaned), 4) if cleaned else 0.0

    def _median(self, values: list[float | None]) -> float:
        cleaned = [float(value) for value in values if value is not None]
        return round(median(cleaned), 4) if cleaned else 0.0

    def _win_rate(self, values: list[float | None]) -> float:
        cleaned = [float(value) for value in values if value is not None]
        return round(sum(1 for value in cleaned if value > 0) / len(cleaned), 4) if cleaned else 0.0
