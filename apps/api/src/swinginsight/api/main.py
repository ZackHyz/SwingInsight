from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from datetime import date

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from swinginsight.api.routes.news import get_segment_news_payload, get_turning_point_news_payload
from swinginsight.api.routes.predictions import get_prediction_payload
from swinginsight.api.routes.refresh import enqueue_stock_refresh, get_stock_refresh_status
from swinginsight.api.routes.segments import get_segment_chart_payload, get_segment_detail_payload
from swinginsight.api.routes.stocks import (
    get_pattern_group_stat_payload,
    get_pattern_score_snapshot,
    get_pattern_similar_cases_payload,
    get_stock_research_payload,
)
from swinginsight.api.routes.turning_points import commit_turning_points
from swinginsight.api.routes.watchlist import get_watchlist_payload
from swinginsight.db.session import get_session_factory as get_default_session_factory, session_scope
from swinginsight.services.feature_materialization_service import get_segment_library_rows
from swinginsight.services.score_validation_service import ScoreValidationService
from swinginsight.services.stock_refresh_service import StockRefreshService
from swinginsight.services.watchlist_refresh_service import WatchlistRefreshService
from swinginsight.api.schemas.turning_points import StockResearchResponse, TurningPointCommitRequest


def create_app(session_factory: Callable[[], Session] | None = None) -> FastAPI:
    app = FastAPI(title="SwingInsight API")
    task_session_factory = session_factory or get_default_session_factory()

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

    def run_refresh_task(task_id: int) -> None:
        session = task_session_factory()
        try:
            StockRefreshService(session).run(task_id)
        finally:
            session.close()

    def run_watchlist_refresh_task(task_id: int) -> None:
        session = task_session_factory()
        try:
            WatchlistRefreshService(session).run(task_id, limit=30)
        finally:
            session.close()

    @app.get("/stocks/{stock_code}", response_model=StockResearchResponse)
    def get_stock(stock_code: str, session: Session = Depends(get_session)) -> dict[str, object]:
        payload = get_stock_research_payload(session=session, stock_code=stock_code)
        if payload is None:
            raise HTTPException(status_code=404, detail="stock not found")
        return payload

    @app.post("/stocks/{stock_code}/refresh")
    def post_stock_refresh(
        stock_code: str,
        background_tasks: BackgroundTasks,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        payload = enqueue_stock_refresh(session=session, stock_code=stock_code)
        if payload["status"] == "queued":
            background_tasks.add_task(run_refresh_task, int(payload["task_id"]))
        return payload

    @app.get("/stocks/{stock_code}/refresh-status")
    def get_refresh_status(stock_code: str, session: Session = Depends(get_session)) -> dict[str, object]:
        payload = get_stock_refresh_status(session=session, stock_code=stock_code)
        if payload is None:
            raise HTTPException(status_code=404, detail="refresh task not found")
        return payload

    @app.post("/stocks/{stock_code}/turning-points/commit")
    def post_turning_points(
        stock_code: str,
        payload: TurningPointCommitRequest,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return commit_turning_points(stock_code=stock_code, payload=payload, session=session)

    @app.get("/stocks/{stock_code}/pattern-score")
    def get_pattern_score(stock_code: str, session: Session = Depends(get_session)) -> dict[str, object]:
        snapshot = get_pattern_score_snapshot(session=session, stock_code=stock_code)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="pattern score not found")
        payload = snapshot["payload"]
        query_end_date = snapshot.get("query_end_date")
        if isinstance(query_end_date, date):
            ScoreValidationService(session).log_pattern_score(
                stock_code=stock_code,
                query_window_id=snapshot.get("query_window_id"),
                query_end_date=query_end_date,
                predicted_win_rate=float(payload.get("win_rate") or 0.0),
                predicted_avg_return=float(payload.get("avg_return") or 0.0),
                sample_count=int(payload.get("sample_count") or 0),
            )
        return payload

    @app.get("/stocks/{stock_code}/similar-cases")
    def get_pattern_similar_cases(stock_code: str, session: Session = Depends(get_session)) -> list[dict[str, object]]:
        payload = get_pattern_similar_cases_payload(session=session, stock_code=stock_code)
        if payload is None:
            raise HTTPException(status_code=404, detail="similar cases not found")
        return payload

    @app.get("/stocks/{stock_code}/group-stat")
    def get_pattern_group_stat(stock_code: str, session: Session = Depends(get_session)) -> dict[str, object]:
        payload = get_pattern_group_stat_payload(session=session, stock_code=stock_code)
        if payload is None:
            raise HTTPException(status_code=404, detail="group stat not found")
        return payload

    @app.get("/stocks/{stock_code}/score-validation")
    def get_score_validation(stock_code: str, session: Session = Depends(get_session)) -> dict[str, object]:
        return ScoreValidationService(session).build_validation_report(stock_code=stock_code)

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

    @app.get("/watchlist")
    def get_watchlist(session: Session = Depends(get_session)) -> dict[str, object]:
        return get_watchlist_payload(session=session)

    @app.post("/watchlist/refresh")
    def refresh_watchlist(background_tasks: BackgroundTasks, session: Session = Depends(get_session)) -> dict[str, object]:
        service = WatchlistRefreshService(session)
        existing = service.latest_status()
        if existing is not None and existing["status"] in {"queued", "running"}:
            return {**existing, "reused": True}

        task = service.enqueue()
        if task.status == "queued":
            background_tasks.add_task(run_watchlist_refresh_task, int(task.id))
        payload = service.latest_status()
        return {**(payload or {}), "reused": False}

    @app.get("/watchlist/refresh-status")
    def get_watchlist_refresh_status(session: Session = Depends(get_session)) -> dict[str, object]:
        payload = WatchlistRefreshService(session).latest_status()
        if payload is None:
            return {
                "task_id": None,
                "status": "idle",
                "created_at": None,
                "start_time": None,
                "end_time": None,
                "updated_at": None,
                "error_message": None,
                "scan_date": None,
                "row_count": None,
            }
        return payload

    @app.get("/predictions/{stock_code}")
    def get_prediction(stock_code: str, predict_date: date, session: Session = Depends(get_session)) -> dict[str, object]:
        return get_prediction_payload(session=session, stock_code=stock_code, predict_date=predict_date)

    return app
