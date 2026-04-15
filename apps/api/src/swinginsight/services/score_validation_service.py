from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.prediction import ScoreLog


class ScoreValidationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def log_pattern_score(
        self,
        *,
        stock_code: str,
        query_window_id: int | None,
        query_end_date: date,
        predicted_win_rate: float,
        predicted_avg_return: float,
        sample_count: int,
    ) -> ScoreLog:
        row = ScoreLog(
            stock_code=stock_code,
            query_window_id=query_window_id,
            query_end_date=query_end_date,
            predicted_win_rate=predicted_win_rate,
            predicted_avg_return=predicted_avg_return,
            sample_count=max(sample_count, 0),
        )
        self.session.add(row)
        self.session.flush()
        return row

    def backfill_actual_returns(self, *, stock_code: str | None = None) -> int:
        query = select(ScoreLog).where((ScoreLog.actual_return_5d.is_(None)) | (ScoreLog.actual_return_10d.is_(None)))
        if stock_code:
            query = query.where(ScoreLog.stock_code == stock_code)
        pending_rows = self.session.scalars(query.order_by(ScoreLog.id.asc())).all()
        updated = 0
        for row in pending_rows:
            if self._backfill_row(row):
                updated += 1
        return updated

    def build_validation_report(self, *, stock_code: str) -> dict[str, object]:
        rows = self.session.scalars(
            select(ScoreLog).where(ScoreLog.stock_code == stock_code).order_by(ScoreLog.id.asc())
        ).all()
        with_5d = [row for row in rows if row.actual_outcome_5d is not None]
        with_10d = [row for row in rows if row.actual_outcome_10d is not None]
        brier_5d = self._brier_score(with_5d, horizon=5)
        brier_10d = self._brier_score(with_10d, horizon=10)
        bins_10d = self._bin_errors(with_10d)
        max_bin_error = max((float(item["abs_error"]) for item in bins_10d if item["sample_count"] > 0), default=1.0)
        pass_gate = len(with_10d) >= 20 and brier_10d <= 0.25 and max_bin_error <= 0.10
        return {
            "stock_code": stock_code,
            "total_logs": len(rows),
            "evaluated_samples_5d": len(with_5d),
            "evaluated_samples_10d": len(with_10d),
            "brier_score_5d": brier_5d,
            "brier_score_10d": brier_10d,
            "win_rate_bin_error_10d": bins_10d,
            "pass_gate": pass_gate,
        }

    def _backfill_row(self, row: ScoreLog) -> bool:
        prices = self.session.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_code == row.stock_code,
                DailyPrice.trade_date >= row.query_end_date,
            )
            .order_by(DailyPrice.trade_date.asc(), DailyPrice.id.asc())
        ).all()
        if not prices:
            return False
        anchor_close = float(prices[0].close_price or 0.0)
        if anchor_close <= 0:
            return False

        changed = False
        if row.actual_return_5d is None and len(prices) > 5:
            ret_5d = float(prices[5].close_price) / anchor_close - 1.0
            row.actual_return_5d = round(ret_5d, 4)
            row.actual_outcome_5d = 1 if ret_5d > 0 else 0
            changed = True
        if row.actual_return_10d is None and len(prices) > 10:
            ret_10d = float(prices[10].close_price) / anchor_close - 1.0
            row.actual_return_10d = round(ret_10d, 4)
            row.actual_outcome_10d = 1 if ret_10d > 0 else 0
            changed = True
        return changed

    def _brier_score(self, rows: list[ScoreLog], *, horizon: int) -> float:
        if not rows:
            return 0.0
        outcomes = [float(getattr(row, f"actual_outcome_{horizon}d")) for row in rows]
        predictions = [float(row.predicted_win_rate) for row in rows]
        score = sum((prediction - outcome) ** 2 for prediction, outcome in zip(predictions, outcomes, strict=False)) / len(rows)
        return round(score, 4)

    def _bin_errors(self, rows: list[ScoreLog]) -> list[dict[str, object]]:
        buckets = [
            {"label": "0.0-0.4", "left": 0.0, "right": 0.4},
            {"label": "0.4-0.6", "left": 0.4, "right": 0.6},
            {"label": "0.6-1.0", "left": 0.6, "right": 1.01},
        ]
        results: list[dict[str, object]] = []
        for bucket in buckets:
            bucket_rows = [
                row
                for row in rows
                if bucket["left"] <= float(row.predicted_win_rate) < bucket["right"]
            ]
            if not bucket_rows:
                results.append(
                    {
                        "range": bucket["label"],
                        "sample_count": 0,
                        "predicted_win_rate": 0.0,
                        "actual_win_rate": 0.0,
                        "abs_error": 0.0,
                    }
                )
                continue
            predicted = sum(float(row.predicted_win_rate) for row in bucket_rows) / len(bucket_rows)
            actual = sum(int(row.actual_outcome_10d or 0) for row in bucket_rows) / len(bucket_rows)
            results.append(
                {
                    "range": bucket["label"],
                    "sample_count": len(bucket_rows),
                    "predicted_win_rate": round(predicted, 4),
                    "actual_win_rate": round(actual, 4),
                    "abs_error": round(abs(predicted - actual), 4),
                }
            )
        return results
