from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice, TradeRecord
from swinginsight.db.models.news import NewsRaw
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.api.routes.predictions import load_latest_prediction_summary


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
    trade_markers = session.scalars(
        select(TradeRecord).where(TradeRecord.stock_code == stock_code).order_by(TradeRecord.trade_date.asc(), TradeRecord.id.asc())
    ).all()
    news_items = session.scalars(
        select(NewsRaw).where(NewsRaw.stock_code == stock_code).order_by(NewsRaw.news_date.desc(), NewsRaw.id.desc()).limit(5)
    ).all()
    prediction = load_latest_prediction_summary(session, stock_code)

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
                "volume": int(row.volume) if row.volume is not None else None,
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
        "trade_markers": [
            {
                "id": row.id,
                "trade_date": row.trade_date.isoformat(),
                "trade_type": row.trade_type,
                "price": float(row.price),
                "quantity": row.quantity,
                "strategy_tag": row.strategy_tag,
                "note": row.note,
            }
            for row in trade_markers
        ],
        "news_items": [
            {
                "news_id": row.id,
                "title": row.title,
                "summary": row.summary,
                "source_name": row.source_name,
                "news_date": row.news_date.isoformat() if row.news_date else None,
            }
            for row in news_items
        ],
        "current_state": prediction
        if prediction
        else {
            "label": "待生成",
            "summary": "预测结果待生成",
            "probabilities": {},
            "key_features": {},
            "risk_flags": {},
            "similar_cases": [],
        },
    }
