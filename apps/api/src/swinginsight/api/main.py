from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import contextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from swinginsight.api.routes.stocks import get_stock_research_payload
from swinginsight.api.routes.turning_points import commit_turning_points
from swinginsight.api.schemas.turning_points import StockResearchResponse, TurningPointCommitRequest
from swinginsight.db.session import session_scope


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

    return app
