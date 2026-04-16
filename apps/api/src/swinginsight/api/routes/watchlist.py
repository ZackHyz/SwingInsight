from __future__ import annotations

from sqlalchemy.orm import Session

from swinginsight.services.market_watchlist_service import MarketWatchlistService


def get_watchlist_payload(session: Session, *, limit: int = 30) -> dict[str, object]:
    return MarketWatchlistService(session).get_latest_watchlist(limit=limit)
