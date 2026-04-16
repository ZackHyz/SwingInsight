from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.news import NewsRaw
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.stock import StockBasic
from swinginsight.db.models.watchlist import MarketScanResult


class MarketWatchlistService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run_scan(self, *, scan_date: date | None = None, top_k: int = 50) -> dict[str, object]:
        resolved_scan_date = scan_date or datetime.now(UTC).date()
        stock_rows = self.session.scalars(select(StockBasic).order_by(StockBasic.stock_code.asc())).all()

        candidates: list[dict[str, object]] = []
        for stock in stock_rows:
            prediction = self.session.scalar(
                select(PredictionResult)
                .where(PredictionResult.stock_code == stock.stock_code)
                .order_by(PredictionResult.predict_date.desc(), PredictionResult.id.desc())
            )
            if prediction is None:
                continue

            pattern_score = float(prediction.up_prob_10d or 0.0)
            confidence = self._resolve_confidence(prediction)
            sample_count = len(prediction.similarity_topn_json or [])
            event_density = self._resolve_event_density(stock.stock_code, scan_date=resolved_scan_date)
            latest_refresh_at = self.session.scalar(
                select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_code == stock.stock_code)
            )
            rank_score = self._rank_score(
                pattern_score=pattern_score,
                confidence=confidence,
                sample_count=sample_count,
                event_density=event_density,
            )
            candidates.append(
                {
                    "stock_code": stock.stock_code,
                    "stock_name": stock.stock_name,
                    "pattern_score": pattern_score,
                    "confidence": confidence,
                    "sample_count": sample_count,
                    "event_density": event_density,
                    "latest_refresh_at": datetime.combine(latest_refresh_at, datetime.min.time()) if latest_refresh_at else None,
                    "rank_score": rank_score,
                    "source_version": prediction.model_version,
                }
            )

        candidates.sort(key=lambda row: (row["rank_score"], row["pattern_score"], row["sample_count"]), reverse=True)
        ranked = candidates[: max(top_k, 1)]

        self.session.execute(delete(MarketScanResult).where(MarketScanResult.scan_date == resolved_scan_date))
        for index, row in enumerate(ranked):
            self.session.add(
                MarketScanResult(
                    scan_date=resolved_scan_date,
                    stock_code=str(row["stock_code"]),
                    stock_name=row["stock_name"],
                    rank_no=index + 1,
                    rank_score=float(row["rank_score"]),
                    pattern_score=float(row["pattern_score"]),
                    confidence=float(row["confidence"]),
                    sample_count=int(row["sample_count"]),
                    event_density=float(row["event_density"]),
                    latest_refresh_at=row["latest_refresh_at"],
                    source_version=row["source_version"],
                )
            )
        self.session.commit()
        return {"scan_date": resolved_scan_date.isoformat(), "rows": len(ranked)}

    def get_latest_watchlist(self, *, limit: int = 30) -> dict[str, object]:
        latest_scan_date = self.session.scalar(select(func.max(MarketScanResult.scan_date)))
        if latest_scan_date is None:
            return {"scan_date": None, "rows": []}
        rows = self.session.scalars(
            select(MarketScanResult)
            .where(MarketScanResult.scan_date == latest_scan_date)
            .order_by(MarketScanResult.rank_no.asc())
            .limit(max(limit, 1))
        ).all()
        return {
            "scan_date": latest_scan_date.isoformat(),
            "rows": [
                {
                    "stock_code": row.stock_code,
                    "stock_name": row.stock_name,
                    "rank_no": row.rank_no,
                    "rank_score": float(row.rank_score),
                    "pattern_score": float(row.pattern_score),
                    "confidence": float(row.confidence),
                    "sample_count": row.sample_count,
                    "event_density": float(row.event_density),
                    "latest_refresh_at": row.latest_refresh_at.isoformat() if row.latest_refresh_at is not None else None,
                }
                for row in rows
            ],
        }

    def _resolve_confidence(self, prediction: PredictionResult) -> float:
        up = float(prediction.up_prob_10d or 0.0)
        down = float(prediction.down_prob_10d or 0.0)
        spread = max(up - down, 0.0)
        return round(min(0.4 + spread, 1.0), 4)

    def _resolve_event_density(self, stock_code: str, *, scan_date: date) -> float:
        from_date = scan_date - timedelta(days=20)
        count = self.session.scalar(
            select(func.count())
            .select_from(NewsRaw)
            .where(
                NewsRaw.stock_code == stock_code,
                NewsRaw.news_date >= from_date,
                NewsRaw.news_date <= scan_date,
            )
        )
        return round(float((count or 0) / 20.0), 4)

    def _rank_score(self, *, pattern_score: float, confidence: float, sample_count: int, event_density: float) -> float:
        sample_component = min(sample_count / 10.0, 1.0)
        event_component = min(event_density / 0.3, 1.0)
        score = pattern_score * 0.5 + confidence * 0.25 + sample_component * 0.15 + event_component * 0.1
        return round(score, 4)
