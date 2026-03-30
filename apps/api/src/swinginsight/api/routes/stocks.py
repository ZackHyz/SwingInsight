from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import TurningPoint


def get_stock_research_payload(session: Session, stock_code: str) -> dict[str, object] | None:
    stock = session.scalar(select(StockBasic).where(StockBasic.stock_code == stock_code))
    if stock is None:
        return None

    prices = session.scalars(
        select(DailyPrice).where(DailyPrice.stock_code == stock_code).order_by(DailyPrice.trade_date.asc())
    ).all()
    auto_points = session.scalars(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.source_type == "system")
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    final_points = session.scalars(
        select(TurningPoint)
        .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
        .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
    ).all()
    prediction = session.scalar(
        select(PredictionResult)
        .where(PredictionResult.stock_code == stock_code)
        .order_by(PredictionResult.predict_date.desc(), PredictionResult.id.desc())
    )

    return {
        "stock": {
            "stock_code": stock.stock_code,
            "stock_name": stock.stock_name,
            "market": stock.market,
            "industry": stock.industry,
            "concept_tags": stock.concept_tags or [],
        },
        "prices": [
            {
                "trade_date": row.trade_date.isoformat(),
                "open_price": float(row.open_price),
                "high_price": float(row.high_price),
                "low_price": float(row.low_price),
                "close_price": float(row.close_price),
            }
            for row in prices
        ],
        "auto_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in auto_points
        ],
        "final_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in final_points
        ],
        "trade_markers": [],
        "current_state": {
            "label": prediction.current_state if prediction else "placeholder",
            "summary": prediction.summary if prediction else "Prediction pending",
        },
    }
