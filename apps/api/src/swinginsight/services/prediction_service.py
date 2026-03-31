from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SegmentFeature, SwingSegment
from swinginsight.domain.prediction.similarity import cosine_similarity
from swinginsight.domain.prediction.state_rules import classify_current_state
from swinginsight.services.feature_materialization_service import materialize_segment_features


PREDICTION_VERSION = "prediction:v1"


@dataclass(slots=True, frozen=True)
class SimilarCase:
    segment_id: int
    stock_code: str
    score: float
    pct_change: float | None


@dataclass(slots=True, frozen=True)
class PredictionOutcome:
    current_state: str
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
    key_features: dict[str, float]
    risk_flags: dict[str, str]
    summary: str


class SimilarityStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def load_feature_vector(self, segment_id: int) -> dict[str, float]:
        rows = self.session.scalars(
            select(SegmentFeature).where(SegmentFeature.segment_id == segment_id).order_by(SegmentFeature.feature_name.asc())
        ).all()
        if not rows:
            materialize_segment_features(self.session, segment_id=segment_id)
            rows = self.session.scalars(
                select(SegmentFeature).where(SegmentFeature.segment_id == segment_id).order_by(SegmentFeature.feature_name.asc())
            ).all()
        return {
            row.feature_name: float(row.feature_value_num or 0.0)
            for row in rows
            if row.feature_value_num is not None
        }

    def find_top_k(self, current_vector: dict[str, float], exclude_segment_id: int, k: int = 5) -> list[SimilarCase]:
        segments = self.session.scalars(select(SwingSegment).where(SwingSegment.id != exclude_segment_id)).all()
        matches: list[SimilarCase] = []
        for segment in segments:
            vector = self.load_feature_vector(segment.id)
            matches.append(
                SimilarCase(
                    segment_id=segment.id,
                    stock_code=segment.stock_code,
                    score=round(cosine_similarity(current_vector, vector), 4),
                    pct_change=float(segment.pct_change) if segment.pct_change is not None else None,
                )
            )
        return sorted(matches, key=lambda item: item.score, reverse=True)[:k]


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
        similar_cases = self.similarity_store.find_top_k(current_vector=current_vector, exclude_segment_id=current_segment.id, k=5)
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
        summary = f"{current_state}，10日上行概率 {probabilities['up_10d']:.2f}"

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
            key_features=key_features,
            risk_flags=risk_flags,
            summary=summary,
        )

    def _estimate_probabilities(self, similar_cases: list[SimilarCase]) -> dict[str, float]:
        if not similar_cases:
            up, flat, down = 0.34, 0.33, 0.33
        else:
            up_weight = 0.0
            flat_weight = 0.0
            down_weight = 0.0
            for case in similar_cases:
                weight = max(case.score, 0.01)
                pct_change = case.pct_change or 0.0
                if pct_change > 3:
                    up_weight += weight
                elif pct_change < -3:
                    down_weight += weight
                else:
                    flat_weight += weight
            total = up_weight + flat_weight + down_weight or 1.0
            up = round(up_weight / total, 4)
            flat = round(flat_weight / total, 4)
            down = round(1.0 - up - flat, 4)
        return {
            "up_5d": up,
            "flat_5d": flat,
            "down_5d": down,
            "up_10d": up,
            "flat_10d": flat,
            "down_10d": down,
            "up_20d": up,
            "flat_20d": flat,
            "down_20d": down,
        }

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
                        "pct_change": case.pct_change,
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
