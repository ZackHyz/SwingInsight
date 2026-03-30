from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import AlgoVersion, DailyPrice, TaskRunLog
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.domain.turning_points.filters import filter_by_min_separation_pct
from swinginsight.domain.turning_points.zigzag import DetectedTurningPoint, ZigZagDetector


@dataclass(slots=True, frozen=True)
class TurningPointRunResult:
    version_code: str
    inserted: int
    points: list[DetectedTurningPoint]


class TurningPointService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def rebuild_points(
        self,
        *,
        stock_code: str,
        algo: str,
        reversal_pct: float = 0.08,
        min_separation_pct: float = 0.05,
    ) -> TurningPointRunResult:
        if algo != "zigzag":
            raise ValueError(f"Unsupported algo: {algo}")

        version_code = f"{algo}:reversal={reversal_pct:.4f}:min_sep={min_separation_pct:.4f}"
        self._upsert_algo_version(
            version_code=version_code,
            algo_type="turning_point",
            params_json={"algo": algo, "reversal_pct": reversal_pct, "min_separation_pct": min_separation_pct},
        )

        prices = self._load_price_series(stock_code)
        detector = ZigZagDetector(reversal_pct=reversal_pct)
        points = filter_by_min_separation_pct(detector.detect(prices), min_separation_pct=min_separation_pct)

        self.session.execute(
            delete(TurningPoint).where(
                TurningPoint.stock_code == stock_code,
                TurningPoint.source_type == "system",
                TurningPoint.version_code == version_code,
            )
        )

        for point in points:
            self.session.add(
                TurningPoint(
                    stock_code=stock_code,
                    point_date=point.point_date,
                    point_type=point.point_type,
                    point_price=point.point_price,
                    confirm_date=point.confirm_date,
                    source_type="system",
                    version_code=version_code,
                    is_final=True,
                    confidence_score=1.0,
                )
            )

        self.session.add(
            TaskRunLog(
                task_name="rebuild_turning_points",
                task_type="turning_point_generation",
                target_code=stock_code,
                status="success",
                start_time=datetime.now(UTC).replace(tzinfo=None),
                end_time=datetime.now(UTC).replace(tzinfo=None),
                input_params_json={"algo": algo, "version_code": version_code},
                result_summary=f"inserted={len(points)}",
            )
        )
        self.session.flush()
        return TurningPointRunResult(version_code=version_code, inserted=len(points), points=points)

    def _load_price_series(self, stock_code: str) -> list[dict[str, Any]]:
        rows = self.session.scalars(
            select(DailyPrice)
            .where(DailyPrice.stock_code == stock_code)
            .order_by(DailyPrice.trade_date.asc())
        ).all()
        return [
            {
                "trade_date": row.trade_date,
                "open_price": float(row.open_price),
                "high_price": float(row.high_price),
                "low_price": float(row.low_price),
                "close_price": float(row.close_price),
            }
            for row in rows
        ]

    def _upsert_algo_version(self, *, version_code: str, algo_type: str, params_json: dict[str, Any]) -> None:
        existing = self.session.scalar(select(AlgoVersion).where(AlgoVersion.version_code == version_code))
        if existing is None:
            self.session.add(
                AlgoVersion(
                    version_code=version_code,
                    algo_type=algo_type,
                    version_name=version_code,
                    params_json=params_json,
                    is_active=True,
                )
            )
