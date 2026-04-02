from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from swinginsight.api.routes.news import get_segment_news_payload, get_turning_point_news_payload
from swinginsight.api.routes.predictions import get_prediction_payload
from swinginsight.api.routes.segments import get_segment_chart_payload, get_segment_detail_payload
from swinginsight.api.routes.stocks import get_stock_research_payload
from swinginsight.api.routes.turning_points import commit_turning_points
from swinginsight.db.session import session_scope
from swinginsight.services.feature_materialization_service import get_segment_library_rows
from swinginsight.services.stock_research_service import StockResearchService
from swinginsight.api.schemas.turning_points import StockResearchResponse, TurningPointCommitRequest


def create_app(session_factory: Callable[[], Session] | None = None) -> FastAPI:
    app = FastAPI(title="SwingInsight API")

    @contextmanager
    def default_session_factory() -> Iterator[Session]:
        with session_scope() as session:
            yield session

    def get_session() -> Iterator[Session]:
        if session_factory is not None:
            yield session_factory()
            return
        with default_session_factory() as session:
            yield session

    @app.get("/stocks/{stock_code}", response_model=StockResearchResponse)
    def get_stock(stock_code: str, session: Session = Depends(get_session)) -> dict[str, object]:
        if not StockResearchService(session).ensure_stock_ready(stock_code):
            raise HTTPException(status_code=404, detail="stock not found")
        payload = get_stock_research_payload(session=session, stock_code=stock_code)
        if payload is None:
            raise HTTPException(status_code=404, detail="stock not found")
        return payload

    @app.post("/stocks/{stock_code}/turning-points/commit")
    def post_turning_points(
        stock_code: str,
        payload: TurningPointCommitRequest,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return commit_turning_points(stock_code=stock_code, payload=payload, session=session)

    @app.get("/segments/{segment_id}")
    def get_segment(segment_id: int, session: Session = Depends(get_session)) -> dict[str, object]:
        payload = get_segment_detail_payload(session=session, segment_id=segment_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="segment not found")
        return payload

    @app.get("/segments/{segment_id}/chart")
    def get_segment_chart(segment_id: int, session: Session = Depends(get_session)) -> dict[str, object]:
        payload = get_segment_chart_payload(session=session, segment_id=segment_id)
        if payload is None:
            raise HTTPException(status_code=404, detail="segment not found")
        return payload

    @app.get("/segments/{segment_id}/news")
    def get_segment_news(segment_id: int, session: Session = Depends(get_session)) -> list[dict[str, object]]:
        return get_segment_news_payload(session=session, segment_id=segment_id)

    @app.get("/turning-points/{point_id}/news")
    def get_turning_point_news(point_id: int, session: Session = Depends(get_session)) -> list[dict[str, object]]:
        return get_turning_point_news_payload(session=session, point_id=point_id)

    @app.get("/library")
    def get_library(session: Session = Depends(get_session)) -> dict[str, object]:
        return {"rows": get_segment_library_rows(session)}

    @app.get("/predictions/{stock_code}")
    def get_prediction(stock_code: str, predict_date: date, session: Session = Depends(get_session)) -> dict[str, object]:
        return get_prediction_payload(session=session, stock_code=stock_code, predict_date=predict_date)

    return app
