from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.pattern import PatternFutureStat, PatternWindow
from swinginsight.db.models.segment import SwingSegment


@dataclass(slots=True, frozen=True)
class PatternBuildResult:
    created: int
    updated: int
    skipped: int


@dataclass(slots=True, frozen=True)
class PatternFutureStatResult:
    updated: int
    skipped: int


class PatternWindowService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def build_windows(self, *, stock_code: str, window_size: int = 7, feature_version: str = "pattern:v1") -> PatternBuildResult:
        rows = self.session.scalars(
            select(DailyPrice)
            .where(DailyPrice.stock_code == stock_code)
            .order_by(DailyPrice.trade_date.asc())
        ).all()
        if len(rows) < window_size:
            return PatternBuildResult(created=0, updated=0, skipped=0)

        created = 0
        updated = 0
        for index in range(len(rows) - window_size + 1):
            window_rows = rows[index : index + window_size]
            start_row = window_rows[0]
            end_row = window_rows[-1]
            center_row = window_rows[window_size // 2]
            window_uid = f"pw-{stock_code}-{start_row.trade_date.isoformat()}-{end_row.trade_date.isoformat()}"
            segment_id = self._lookup_segment_id(stock_code=stock_code, anchor_date=center_row.trade_date)
            start_close = float(start_row.close_price or 0)
            end_close = float(end_row.close_price or 0)
            period_pct_change = ((end_close / start_close) - 1.0) * 100 if start_close else None

            high_prices = [float(row.high_price or row.close_price or 0) for row in window_rows]
            low_prices = [float(row.low_price or row.close_price or 0) for row in window_rows]

            payload = {
                "stock_code": stock_code,
                "segment_id": segment_id,
                "start_date": start_row.trade_date,
                "end_date": end_row.trade_date,
                "window_size": window_size,
                "start_close": start_close,
                "end_close": end_close,
                "period_pct_change": period_pct_change,
                "highest_day_pos": high_prices.index(max(high_prices)) if high_prices else None,
                "lowest_day_pos": low_prices.index(min(low_prices)) if low_prices else None,
                "trend_label": self._trend_label(start_close=start_close, end_close=end_close),
                "feature_version": feature_version,
            }

            existing = self.session.scalar(select(PatternWindow).where(PatternWindow.window_uid == window_uid))
            if existing is None:
                self.session.add(PatternWindow(window_uid=window_uid, **payload))
                created += 1
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
                updated += 1

        self.session.flush()
        return PatternBuildResult(created=created, updated=updated, skipped=0)

    def materialize_future_stats(self, *, stock_code: str) -> PatternFutureStatResult:
        windows = self.session.scalars(
            select(PatternWindow)
            .where(PatternWindow.stock_code == stock_code)
            .order_by(PatternWindow.end_date.asc(), PatternWindow.id.asc())
        ).all()
        updated = 0
        skipped = 0
        for window in windows:
            anchor_close = float(window.end_close or 0)
            future_rows = self.session.scalars(
                select(DailyPrice)
                .where(DailyPrice.stock_code == stock_code, DailyPrice.trade_date >= window.end_date)
                .order_by(DailyPrice.trade_date.asc())
            ).all()
            if anchor_close <= 0 or len(future_rows) <= 1:
                skipped += 1
                continue

            payload = {
                "ret_1d": self._future_return(future_rows, anchor_close=anchor_close, horizon=1),
                "ret_3d": self._future_return(future_rows, anchor_close=anchor_close, horizon=3),
                "ret_5d": self._future_return(future_rows, anchor_close=anchor_close, horizon=5),
                "ret_10d": self._future_return(future_rows, anchor_close=anchor_close, horizon=10),
                "max_up_3d": self._window_extreme(future_rows, anchor_close=anchor_close, horizon=3, fn=max),
                "max_dd_3d": self._window_extreme(future_rows, anchor_close=anchor_close, horizon=3, fn=min),
                "max_up_5d": self._window_extreme(future_rows, anchor_close=anchor_close, horizon=5, fn=max),
                "max_dd_5d": self._window_extreme(future_rows, anchor_close=anchor_close, horizon=5, fn=min),
                "max_up_10d": self._window_extreme(future_rows, anchor_close=anchor_close, horizon=10, fn=max),
                "max_dd_10d": self._window_extreme(future_rows, anchor_close=anchor_close, horizon=10, fn=min),
            }

            existing = self.session.scalar(select(PatternFutureStat).where(PatternFutureStat.window_id == window.id))
            if existing is None:
                self.session.add(PatternFutureStat(window_id=window.id, **payload))
            else:
                for key, value in payload.items():
                    setattr(existing, key, value)
            updated += 1

        self.session.flush()
        return PatternFutureStatResult(updated=updated, skipped=skipped)

    def _lookup_segment_id(self, *, stock_code: str, anchor_date) -> int | None:
        return self.session.scalar(
            select(SwingSegment.id)
            .where(
                SwingSegment.stock_code == stock_code,
                SwingSegment.is_final.is_(True),
                SwingSegment.start_date <= anchor_date,
                SwingSegment.end_date >= anchor_date,
            )
            .order_by(SwingSegment.end_date.asc(), SwingSegment.id.asc())
        )

    def _trend_label(self, *, start_close: float, end_close: float) -> str:
        if start_close <= 0:
            return "sideways"
        ratio = end_close / start_close
        if ratio >= 1.01:
            return "uptrend"
        if ratio <= 0.99:
            return "downtrend"
        return "sideways"

    def _future_return(self, rows: list[DailyPrice], *, anchor_close: float, horizon: int) -> float | None:
        if len(rows) <= horizon:
            return None
        return float(rows[horizon].close_price) / anchor_close - 1.0

    def _window_extreme(self, rows: list[DailyPrice], *, anchor_close: float, horizon: int, fn) -> float | None:
        if len(rows) <= horizon:
            return None
        values = [float(row.close_price) / anchor_close - 1.0 for row in rows[1 : horizon + 1]]
        return fn(values) if values else None
