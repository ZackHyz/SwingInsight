from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.prediction import PredictionResult
from swinginsight.services.prediction_service import PredictionService


def get_prediction_payload(session: Session, stock_code: str, predict_date: date) -> dict[str, object]:
    result = PredictionService(session).predict(stock_code, predict_date)
    return {
        "stock_code": stock_code,
        "predict_date": predict_date.isoformat(),
        "current_state": result.current_state,
        "summary": result.summary,
        "probabilities": {
            "up_5d": result.up_prob_5d,
            "flat_5d": result.flat_prob_5d,
            "down_5d": result.down_prob_5d,
            "up_10d": result.up_prob_10d,
            "flat_10d": result.flat_prob_10d,
            "down_10d": result.down_prob_10d,
            "up_20d": result.up_prob_20d,
            "flat_20d": result.flat_prob_20d,
            "down_20d": result.down_prob_20d,
        },
        "key_features": result.key_features,
        "risk_flags": result.risk_flags,
        "similar_cases": [
            {
                "segment_id": case.segment_id,
                "stock_code": case.stock_code,
                "score": case.score,
                "pct_change": case.pct_change,
            }
            for case in result.similar_cases
        ],
    }


def load_latest_prediction_summary(session: Session, stock_code: str) -> dict[str, object] | None:
    prediction = session.scalar(
        select(PredictionResult)
        .where(PredictionResult.stock_code == stock_code)
        .order_by(PredictionResult.predict_date.desc(), PredictionResult.id.desc())
    )
    if prediction is None:
        return None
    return {
        "label": prediction.current_state,
        "summary": prediction.summary or "Prediction pending",
        "probabilities": {
            "up_5d": float(prediction.up_prob_5d or 0),
            "flat_5d": float(prediction.flat_prob_5d or 0),
            "down_5d": float(prediction.down_prob_5d or 0),
            "up_10d": float(prediction.up_prob_10d or 0),
            "flat_10d": float(prediction.flat_prob_10d or 0),
            "down_10d": float(prediction.down_prob_10d or 0),
            "up_20d": float(prediction.up_prob_20d or 0),
            "flat_20d": float(prediction.flat_prob_20d or 0),
            "down_20d": float(prediction.down_prob_20d or 0),
        },
        "key_features": prediction.key_features_json or {},
        "risk_flags": prediction.risk_flags_json or {},
        "similar_cases": prediction.similarity_topn_json or [],
    }
