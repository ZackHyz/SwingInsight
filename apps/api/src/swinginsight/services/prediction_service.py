from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from math import sqrt
from statistics import mean, median

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SegmentFeature, SwingSegment
from swinginsight.domain.prediction.similarity import (
    PATTERN_FEATURES,
    PATTERN_COMPONENT_WEIGHT,
    PRICE_FEATURES,
    PRICE_COMPONENT_WEIGHT,
    TURNOVER_FEATURES,
    TURNOVER_COMPONENT_WEIGHT,
    VOLUME_FEATURES,
    VOLUME_COMPONENT_WEIGHT,
    bar_count_similarity,
    blend_scores,
    build_standardized_vectors,
    component_similarity,
    sequence_similarity,
    trajectory_similarity,
)
from swinginsight.domain.prediction.state_rules import classify_current_state
from swinginsight.services.feature_materialization_service import materialize_segment_features


PREDICTION_VERSION = "prediction:v2-pattern"
PROBABILITY_PRIORS = {"up": 0.30, "flat": 0.25, "down": 0.45}
PRIOR_STRENGTH = 2.0
SEQUENCE_WINDOW = 10
SUMMARY_BLEND_WEIGHT = 0.35
SEQUENCE_BLEND_WEIGHT = 0.65
PRICE_SUMMARY_BLEND_WEIGHT = 0.2
PRICE_SEQUENCE_BLEND_WEIGHT = 0.35
PRICE_TRAJECTORY_BLEND_WEIGHT = 0.45
PATTERN_SUMMARY_BLEND_WEIGHT = 0.2
PATTERN_SEQUENCE_BLEND_WEIGHT = 0.8
PREDICTION_HORIZONS = (1, 5, 10, 20)
SIMILAR_CASE_RETURN_HORIZONS = (1, 3, 5, 10)
FORWARD_RETURN_HORIZONS = tuple(sorted({*PREDICTION_HORIZONS, *SIMILAR_CASE_RETURN_HORIZONS}))
BAR_COUNT_BLEND_WEIGHT = 0.05


def log_safe(value: float) -> float:
    if value <= 0:
        return 0.0
    return value if value < 1 else 1 + (value - 1) * 0.5


@dataclass(slots=True, frozen=True)
class SimilarCase:
    segment_id: int
    stock_code: str
    score: float
    price_score: float
    volume_score: float
    turnover_score: float
    pattern_score: float
    pct_change: float | None
    start_date: date
    end_date: date
    forward_returns: dict[int, float | None]
    window_id: int | None = None
    window_start_date: date | None = None
    window_end_date: date | None = None
    window_size: int | None = None
    segment_start_date: date | None = None
    segment_end_date: date | None = None
    candle_score: float | None = None
    trend_score: float | None = None
    vola_score: float | None = None


@dataclass(slots=True, frozen=True)
class PredictionOutcome:
    current_state: str
    up_prob_1d: float
    flat_prob_1d: float
    down_prob_1d: float
    up_prob_5d: float
    flat_prob_5d: float
    down_prob_5d: float
    up_prob_10d: float
    flat_prob_10d: float
    down_prob_10d: float
    up_prob_20d: float
    flat_prob_20d: float
    down_prob_20d: float
    similar_cases: list[SimilarCase]
    group_stat: dict[str, float]
    query_window: dict[str, object] | None
    key_features: dict[str, float]
    risk_flags: dict[str, str]
    summary: str
    fallback_used: bool
    fallback_reason: str | None
    fallback_error_type: str | None
    fallback_stage: str | None


class SimilarityStore:
    def __init__(self, session: Session) -> None:
        self.session = session
        self._feature_cache: dict[int, dict[str, float]] = {}
        self._price_cache: dict[int, list[DailyPrice]] = {}
        self._sequence_cache: dict[int, dict[str, list[float]]] = {}
        self._forward_return_cache: dict[int, dict[int, float | None]] = {}

    def load_feature_vector(self, segment_id: int) -> dict[str, float]:
        cached = self._feature_cache.get(segment_id)
        if cached is not None:
            return cached
        rows = self.session.scalars(
            select(SegmentFeature).where(SegmentFeature.segment_id == segment_id).order_by(SegmentFeature.feature_name.asc())
        ).all()
        if not rows:
            materialize_segment_features(self.session, segment_id=segment_id)
            rows = self.session.scalars(
                select(SegmentFeature).where(SegmentFeature.segment_id == segment_id).order_by(SegmentFeature.feature_name.asc())
            ).all()
        vector = {
            row.feature_name: float(row.feature_value_num or 0.0)
            for row in rows
            if row.feature_value_num is not None
        }
        self._feature_cache[segment_id] = vector
        return vector

    def find_top_k(self, current_segment: SwingSegment, current_vector: dict[str, float], k: int = 5) -> list[SimilarCase]:
        segments = self._load_candidate_segments(current_segment=current_segment, k=k)
        candidate_vectors: list[dict[str, float]] = []
        candidate_segments: list[SwingSegment] = []
        current_bar_count = len(self._load_price_rows(current_segment))
        for segment in segments:
            candidate_segments.append(segment)
            candidate_vectors.append(self.load_feature_vector(segment.id))

        if not candidate_segments:
            return []

        standardized_vectors = build_standardized_vectors([current_vector, *candidate_vectors])
        standardized_current = standardized_vectors[0]
        standardized_candidates = standardized_vectors[1:]
        current_sequences = self.load_sequence_components(current_segment)
        matches: list[tuple[tuple[int, int, int, float, int, date, int], SimilarCase]] = []
        for segment, vector in zip(candidate_segments, standardized_candidates, strict=False):
            candidate_sequences = self.load_sequence_components(segment)
            candidate_bar_count = len(self._load_price_rows(segment))
            price_score = blend_scores(
                (PRICE_SUMMARY_BLEND_WEIGHT, component_similarity(standardized_current, vector, PRICE_FEATURES)),
                (PRICE_SEQUENCE_BLEND_WEIGHT, sequence_similarity(current_sequences["price"], candidate_sequences["price"], scale=5.5)),
                (
                    PRICE_TRAJECTORY_BLEND_WEIGHT,
                    trajectory_similarity(current_sequences["trajectory"], candidate_sequences["trajectory"], scale=5.0),
                ),
            )
            volume_score = blend_scores(
                (SUMMARY_BLEND_WEIGHT, component_similarity(standardized_current, vector, VOLUME_FEATURES)),
                (SEQUENCE_BLEND_WEIGHT, sequence_similarity(current_sequences["volume"], candidate_sequences["volume"], scale=4.5)),
            )
            turnover_score = blend_scores(
                (SUMMARY_BLEND_WEIGHT, component_similarity(standardized_current, vector, TURNOVER_FEATURES)),
                (SEQUENCE_BLEND_WEIGHT, sequence_similarity(current_sequences["turnover"], candidate_sequences["turnover"], scale=4.5)),
            )
            pattern_score = blend_scores(
                (PATTERN_SUMMARY_BLEND_WEIGHT, component_similarity(standardized_current, vector, PATTERN_FEATURES)),
                (PATTERN_SEQUENCE_BLEND_WEIGHT, sequence_similarity(current_sequences["pattern"], candidate_sequences["pattern"], scale=6.5)),
            )
            score = blend_scores(
                (PRICE_COMPONENT_WEIGHT, price_score),
                (VOLUME_COMPONENT_WEIGHT, volume_score),
                (TURNOVER_COMPONENT_WEIGHT, turnover_score),
                (PATTERN_COMPONENT_WEIGHT, pattern_score),
            )
            bar_count_score = bar_count_similarity(current_bar_count, candidate_bar_count)
            score = blend_scores((1.0 - BAR_COUNT_BLEND_WEIGHT, score), (BAR_COUNT_BLEND_WEIGHT, bar_count_score))
            case = SimilarCase(
                segment_id=segment.id,
                stock_code=segment.stock_code,
                score=score,
                price_score=price_score,
                volume_score=volume_score,
                turnover_score=turnover_score,
                pattern_score=pattern_score,
                pct_change=float(segment.pct_change) if segment.pct_change is not None else None,
                start_date=segment.start_date,
                end_date=segment.end_date,
                forward_returns=self.load_forward_returns(segment),
            )
            matches.append(
                (
                    self._segment_priority(
                        segment=segment,
                        current_segment=current_segment,
                        score=score,
                        current_bar_count=current_bar_count,
                        candidate_bar_count=candidate_bar_count,
                    ),
                    case,
                )
            )
        return [case for _, case in sorted(matches, key=lambda item: item[0])[:k]]

    def load_sequence_components(self, segment: SwingSegment) -> dict[str, list[float]]:
        cached = self._sequence_cache.get(segment.id)
        if cached is not None:
            return cached
        rows = self._load_price_rows(segment)
        tail_rows = rows[-SEQUENCE_WINDOW:] if len(rows) >= SEQUENCE_WINDOW else rows
        if not tail_rows:
            sequence = {"price": [], "volume": [], "turnover": [], "pattern": [], "trajectory": []}
            self._sequence_cache[segment.id] = sequence
            return sequence

        padded_rows = [tail_rows[0]] * max(SEQUENCE_WINDOW - len(tail_rows), 0) + tail_rows
        anchor_close = float(padded_rows[0].close_price or 0) or 1.0
        average_volume = sum(float(row.volume or 0) for row in padded_rows) / len(padded_rows) or 1.0
        average_turnover = sum(float(row.turnover_rate or 0) for row in padded_rows) / len(padded_rows) or 1.0
        previous_close = float(padded_rows[0].close_price or 0) or anchor_close

        price_vector: list[float] = []
        volume_vector: list[float] = []
        turnover_vector: list[float] = []
        pattern_vector: list[float] = []
        trajectory_vector = [(float(row.close_price or 0) / anchor_close - 1.0) if anchor_close else 0.0 for row in rows]
        for row in padded_rows:
            open_price = float(row.open_price or 0)
            high_price = float(row.high_price or 0)
            low_price = float(row.low_price or 0)
            close_price = float(row.close_price or 0)
            reference_price = open_price or close_price or 1.0

            price_vector.extend(
                [
                    close_price / anchor_close - 1.0,
                    close_price / previous_close - 1.0 if previous_close else 0.0,
                ]
            )
            volume_vector.append(log_safe(float(row.volume or 0) / average_volume))
            turnover_vector.append(log_safe(float(row.turnover_rate or 0) / average_turnover))
            pattern_vector.extend(
                [
                    (close_price - open_price) / reference_price,
                    (high_price - max(open_price, close_price)) / reference_price,
                    (min(open_price, close_price) - low_price) / reference_price,
                    (high_price - low_price) / reference_price,
                ]
            )
            previous_close = close_price or previous_close

        sequence = {
            "price": price_vector,
            "volume": volume_vector,
            "turnover": turnover_vector,
            "pattern": pattern_vector,
            "trajectory": trajectory_vector,
        }
        self._sequence_cache[segment.id] = sequence
        return sequence

    def load_forward_returns(self, segment: SwingSegment) -> dict[int, float | None]:
        cached = self._forward_return_cache.get(segment.id)
        if cached is not None:
            return cached
        rows = self.session.scalars(
            select(DailyPrice)
            .where(DailyPrice.stock_code == segment.stock_code, DailyPrice.trade_date >= segment.end_date)
            .order_by(DailyPrice.trade_date.asc())
        ).all()
        if not rows:
            forward_returns = {horizon: None for horizon in FORWARD_RETURN_HORIZONS}
            self._forward_return_cache[segment.id] = forward_returns
            return forward_returns

        anchor_close = float(rows[0].close_price or 0)
        if anchor_close == 0:
            forward_returns = {horizon: None for horizon in FORWARD_RETURN_HORIZONS}
            self._forward_return_cache[segment.id] = forward_returns
            return forward_returns

        forward_returns = {
            horizon: (float(rows[horizon].close_price) / anchor_close - 1.0) if len(rows) > horizon else None
            for horizon in FORWARD_RETURN_HORIZONS
        }
        self._forward_return_cache[segment.id] = forward_returns
        return forward_returns

    def _load_candidate_segments(self, *, current_segment: SwingSegment, k: int) -> list[SwingSegment]:
        return self.session.scalars(
            select(SwingSegment)
            .where(SwingSegment.id != current_segment.id)
            .order_by(SwingSegment.end_date.asc(), SwingSegment.id.asc())
        ).all()

    def _segment_priority(
        self,
        *,
        segment: SwingSegment,
        current_segment: SwingSegment,
        score: float,
        current_bar_count: int,
        candidate_bar_count: int,
    ) -> tuple[int, int, int, float, int, date, int]:
        bar_count_gap = abs(candidate_bar_count - current_bar_count)
        return (
            0 if segment.stock_code == current_segment.stock_code else 1,
            0 if self._matches_segment_shape(segment=segment, current_segment=current_segment) else 1,
            self._bar_count_compatibility_band(current_bar_count=current_bar_count, candidate_bar_count=candidate_bar_count),
            -score,
            bar_count_gap,
            segment.end_date,
            segment.id,
        )

    def _bar_count_compatibility_band(self, *, current_bar_count: int, candidate_bar_count: int) -> int:
        if current_bar_count <= 0 or candidate_bar_count <= 0:
            return 2
        ratio = candidate_bar_count / current_bar_count
        if 0.5 <= ratio <= 1.8:
            return 0
        if 0.35 <= ratio <= 2.2:
            return 1
        return 2

    def _matches_segment_shape(self, *, segment: SwingSegment, current_segment: SwingSegment) -> bool:
        return (
            segment.segment_type == current_segment.segment_type
            and segment.start_point_type == current_segment.start_point_type
            and segment.end_point_type == current_segment.end_point_type
        )

    def _load_price_rows(self, segment: SwingSegment) -> list[DailyPrice]:
        cached = self._price_cache.get(segment.id)
        if cached is not None:
            return cached
        rows = self.session.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_code == segment.stock_code,
                DailyPrice.trade_date >= segment.start_date,
                DailyPrice.trade_date <= segment.end_date,
            )
            .order_by(DailyPrice.trade_date.asc())
        ).all()
        self._price_cache[segment.id] = rows
        return rows


class PredictionService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.similarity_store = SimilarityStore(session)

    def predict(self, stock_code: str, predict_date: date) -> PredictionOutcome:
        current_segment = self.session.scalar(
            select(SwingSegment)
            .where(SwingSegment.stock_code == stock_code, SwingSegment.end_date <= predict_date, SwingSegment.is_final.is_(True))
            .order_by(SwingSegment.end_date.desc(), SwingSegment.id.desc())
        )
        if current_segment is None:
            raise ValueError(f"no segment available for {stock_code}")

        current_vector = self.similarity_store.load_feature_vector(current_segment.id)
        current_state = classify_current_state(current_vector)
        pattern_result = None
        fallback_used = False
        fallback_reason: str | None = None
        fallback_error_type: str | None = None
        fallback_stage: str | None = None
        try:
            from swinginsight.services.pattern_similarity_service import PatternSimilarityService
        except Exception as exc:
            fallback_used = True
            fallback_reason = "pattern_similarity_error"
            fallback_error_type = type(exc).__name__
            fallback_stage = "pattern_similarity_import"
        else:
            try:
                with self.session.begin_nested():
                    pattern_result = PatternSimilarityService(self.session).find_similar_windows(
                        current_segment=current_segment,
                        top_k=5,
                    )
            except Exception as exc:
                fallback_used = True
                fallback_reason = "pattern_similarity_error"
                fallback_error_type = type(exc).__name__
                fallback_stage = "pattern_similarity_query"
        if pattern_result is not None and pattern_result.similar_cases:
            similar_cases = pattern_result.similar_cases
            group_stat = pattern_result.group_stat
            query_window = pattern_result.query_window
        else:
            if not fallback_used:
                fallback_used = True
                fallback_reason = self._expected_pattern_fallback_reason(pattern_result)
                fallback_stage = "pattern_similarity_query"
            similar_cases = self.similarity_store.find_top_k(current_segment=current_segment, current_vector=current_vector, k=5)
            group_stat = self._summarize_future_returns(similar_cases)
            query_window = None
        probabilities = self._estimate_probabilities(similar_cases)
        key_features = {
            key: value
            for key, value in current_vector.items()
            if key in {"pct_change", "volume_ratio_5d", "positive_news_ratio", "max_drawdown_pct"}
        }
        risk_flags = {
            "pullback_risk": "high" if current_vector.get("max_drawdown_pct", 0) <= -8 else "low",
            "news_support": "strong" if current_vector.get("positive_news_ratio", 0) >= 0.5 else "weak",
        }
        summary = f"{current_state}，次日上行概率 {probabilities['up_1d']:.2f}，10日上行概率 {probabilities['up_10d']:.2f}"

        self._persist_result(
            stock_code=stock_code,
            predict_date=predict_date,
            current_state=current_state,
            probabilities=probabilities,
            similar_cases=similar_cases,
            key_features=key_features,
            risk_flags=risk_flags,
            summary=summary,
        )

        return PredictionOutcome(
            current_state=current_state,
            up_prob_1d=probabilities["up_1d"],
            flat_prob_1d=probabilities["flat_1d"],
            down_prob_1d=probabilities["down_1d"],
            up_prob_5d=probabilities["up_5d"],
            flat_prob_5d=probabilities["flat_5d"],
            down_prob_5d=probabilities["down_5d"],
            up_prob_10d=probabilities["up_10d"],
            flat_prob_10d=probabilities["flat_10d"],
            down_prob_10d=probabilities["down_10d"],
            up_prob_20d=probabilities["up_20d"],
            flat_prob_20d=probabilities["flat_20d"],
            down_prob_20d=probabilities["down_20d"],
            similar_cases=similar_cases,
            group_stat=group_stat,
            query_window=query_window,
            key_features=key_features,
            risk_flags=risk_flags,
            summary=summary,
            fallback_used=fallback_used,
            fallback_reason=fallback_reason,
            fallback_error_type=fallback_error_type,
            fallback_stage=fallback_stage,
        )

    def _expected_pattern_fallback_reason(self, pattern_result: object | None) -> str:
        if pattern_result is None or getattr(pattern_result, "query_window", None) is None:
            return "no_pattern_window"
        return "no_similar_pattern_cases"

    def _summarize_future_returns(self, similar_cases: list[SimilarCase]) -> dict[str, float]:
        def _mean(values: list[float | None]) -> float:
            cleaned = [float(value) for value in values if value is not None]
            return round(mean(cleaned), 4) if cleaned else 0.0

        def _median(values: list[float | None]) -> float:
            cleaned = [float(value) for value in values if value is not None]
            return round(median(cleaned), 4) if cleaned else 0.0

        def _win_rate(values: list[float | None]) -> float:
            cleaned = [float(value) for value in values if value is not None]
            return round(sum(1 for value in cleaned if value > 0) / len(cleaned), 4) if cleaned else 0.0

        return {
            "sample_count": float(len(similar_cases)),
            "future_1d_mean": _mean([case.forward_returns.get(1) for case in similar_cases]),
            "future_1d_median": _median([case.forward_returns.get(1) for case in similar_cases]),
            "future_1d_win_rate": _win_rate([case.forward_returns.get(1) for case in similar_cases]),
            "future_3d_mean": _mean([case.forward_returns.get(3) for case in similar_cases]),
            "future_5d_mean": _mean([case.forward_returns.get(5) for case in similar_cases]),
            "future_10d_mean": _mean([case.forward_returns.get(10) for case in similar_cases]),
            "future_5d_max_dd_median": 0.0,
            "future_10d_max_dd_median": 0.0,
        }

    def _estimate_probabilities(self, similar_cases: list[SimilarCase]) -> dict[str, float]:
        probabilities: dict[str, float] = {}
        for horizon in PREDICTION_HORIZONS:
            up, flat, down = self._estimate_horizon_probabilities(similar_cases, horizon=horizon)
            probabilities[f"up_{horizon}d"] = up
            probabilities[f"flat_{horizon}d"] = flat
            probabilities[f"down_{horizon}d"] = down
        return probabilities

    def _estimate_horizon_probabilities(self, similar_cases: list[SimilarCase], *, horizon: int) -> tuple[float, float, float]:
        up_weight = PROBABILITY_PRIORS["up"] * PRIOR_STRENGTH
        flat_weight = PROBABILITY_PRIORS["flat"] * PRIOR_STRENGTH
        down_weight = PROBABILITY_PRIORS["down"] * PRIOR_STRENGTH
        flat_band = 0.008 * sqrt(horizon)

        for case in similar_cases:
            future_return = case.forward_returns.get(horizon)
            if future_return is None:
                continue
            weight = max(case.score, 0.01)
            if future_return > flat_band:
                up_weight += weight
            elif future_return < -flat_band:
                down_weight += weight
            else:
                flat_weight += weight

        total = up_weight + flat_weight + down_weight or 1.0
        up = round(up_weight / total, 4)
        flat = round(flat_weight / total, 4)
        down = round(1.0 - up - flat, 4)
        return up, flat, down

    def _persist_result(
        self,
        *,
        stock_code: str,
        predict_date: date,
        current_state: str,
        probabilities: dict[str, float],
        similar_cases: list[SimilarCase],
        key_features: dict[str, float],
        risk_flags: dict[str, str],
        summary: str,
    ) -> None:
        self.session.execute(
            delete(PredictionResult).where(
                PredictionResult.stock_code == stock_code,
                PredictionResult.predict_date == predict_date,
                PredictionResult.model_version == PREDICTION_VERSION,
            )
        )
        self.session.flush()
        self.session.add(
            PredictionResult(
                stock_code=stock_code,
                predict_date=predict_date,
                current_state=current_state,
                up_prob_5d=probabilities["up_5d"],
                flat_prob_5d=probabilities["flat_5d"],
                down_prob_5d=probabilities["down_5d"],
                up_prob_10d=probabilities["up_10d"],
                flat_prob_10d=probabilities["flat_10d"],
                down_prob_10d=probabilities["down_10d"],
                up_prob_20d=probabilities["up_20d"],
                flat_prob_20d=probabilities["flat_20d"],
                down_prob_20d=probabilities["down_20d"],
                similarity_topn_json=[
                    {
                        "segment_id": case.segment_id,
                        "stock_code": case.stock_code,
                        "score": case.score,
                        "price_score": case.price_score,
                        "volume_score": case.volume_score,
                        "turnover_score": case.turnover_score,
                        "pattern_score": case.pattern_score,
                        "window_id": case.window_id,
                        "window_start_date": case.window_start_date.isoformat() if case.window_start_date else None,
                        "window_end_date": case.window_end_date.isoformat() if case.window_end_date else None,
                        "window_size": case.window_size,
                        "segment_start_date": case.segment_start_date.isoformat() if case.segment_start_date else None,
                        "segment_end_date": case.segment_end_date.isoformat() if case.segment_end_date else None,
                        "candle_score": case.candle_score,
                        "trend_score": case.trend_score,
                        "vola_score": case.vola_score,
                        "pct_change": case.pct_change,
                        "start_date": case.start_date.isoformat(),
                        "end_date": case.end_date.isoformat(),
                        **{
                            f"return_{horizon}d": case.forward_returns.get(horizon)
                            for horizon in SIMILAR_CASE_RETURN_HORIZONS
                        },
                    }
                    for case in similar_cases
                ],
                key_features_json=key_features,
                risk_flags_json=risk_flags,
                model_version=PREDICTION_VERSION,
                summary=summary,
            )
        )
        self.session.flush()
