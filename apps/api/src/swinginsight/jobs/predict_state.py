from __future__ import annotations

from datetime import date

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.services.prediction_service import PredictionOutcome, PredictionService


def predict_state(*, stock_code: str, predict_date: date | None) -> PredictionOutcome:
    if predict_date is None:
        raise ValueError("predict_date is required")
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        return PredictionService(session).predict(stock_code, predict_date)
