from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.prediction import PredictionResult
from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.turning_point import PointRevisionLog, TurningPoint
from swinginsight.services.feature_materialization_service import materialize_segment_features
from swinginsight.services.prediction_service import PredictionService
from swinginsight.services.segment_generation_service import SegmentGenerationService
from swinginsight.services.turning_point_service import TurningPointService


MANUAL_VERSION_CODE = "manual:latest"


@dataclass(slots=True, frozen=True)
class ManualTurningPointCommitResult:
    version_code: str
    segment_count: int
    feature_count: int
    prediction_count: int
    final_points: list[TurningPoint]
    latest_prediction: PredictionResult | None


class ManualTurningPointService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def commit_final_points(
        self,
        *,
        stock_code: str,
        operator: str | None,
        final_points: list[dict[str, object]],
        operations: list[dict[str, object]],
    ) -> ManualTurningPointCommitResult:
        final_points = self._normalize_final_points(final_points=final_points, operations=operations)
        self._validate_final_points(final_points)
        protected_manual_pairs = {
            self._point_date_type_key(self._normalize_point_row(new_value))
            for operation in operations
            if isinstance(operation.get("new_value"), dict)
            for new_value in [operation["new_value"]]
        }

        self.session.execute(
            update(TurningPoint)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
            .values(is_final=False)
        )
        self.session.execute(
            delete(TurningPoint).where(
                TurningPoint.stock_code == stock_code,
                TurningPoint.source_type == "manual",
                TurningPoint.version_code == MANUAL_VERSION_CODE,
            )
        )
        self.session.execute(
            delete(SwingSegment).where(
                SwingSegment.stock_code == stock_code,
                SwingSegment.is_final.is_(True),
            )
        )

        for operation in operations:
            self.session.add(
                PointRevisionLog(
                    stock_code=stock_code,
                    operation_type=str(operation["operation_type"]),
                    old_value_json=operation.get("old_value"),
                    new_value_json=operation.get("new_value"),
                    operator=operator,
                )
            )

        created_points: list[TurningPoint] = []
        for row in final_points:
            point = TurningPoint(
                stock_code=stock_code,
                point_date=row["point_date"],
                point_type=str(row["point_type"]),
                point_price=float(row["point_price"]),
                source_type="manual",
                version_code=MANUAL_VERSION_CODE,
                is_final=True,
                created_by=operator,
            )
            self.session.add(point)
            created_points.append(point)

        self.session.flush()
        TurningPointService(self.session).rebuild_points(
            stock_code=stock_code,
            algo="zigzag",
            mark_as_final=False,
        )
        self._promote_inherited_system_points(stock_code=stock_code, protected_manual_pairs=protected_manual_pairs)
        segment_result = SegmentGenerationService(self.session).rebuild_segments(
            stock_code=stock_code,
            version_code=MANUAL_VERSION_CODE,
        )
        rebuilt_segments = self.session.scalars(
            select(SwingSegment)
            .where(
                SwingSegment.stock_code == stock_code,
                SwingSegment.source_version == MANUAL_VERSION_CODE,
                SwingSegment.is_final.is_(True),
            )
            .order_by(SwingSegment.end_date.asc(), SwingSegment.id.asc())
        ).all()
        feature_count = 0
        for segment in rebuilt_segments:
            feature_count += len(materialize_segment_features(self.session, segment.id))

        latest_trade_date = self.session.scalar(select(func.max(DailyPrice.trade_date)).where(DailyPrice.stock_code == stock_code))
        latest_prediction: PredictionResult | None = None
        prediction_count = 0
        if latest_trade_date is not None and rebuilt_segments:
            PredictionService(self.session).predict(stock_code, latest_trade_date)
            latest_prediction = self.session.scalar(
                select(PredictionResult)
                .where(PredictionResult.stock_code == stock_code)
                .order_by(PredictionResult.predict_date.desc(), PredictionResult.id.desc())
            )
            prediction_count = 1
        final_rows = self.session.scalars(
            select(TurningPoint)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()
        return ManualTurningPointCommitResult(
            version_code=MANUAL_VERSION_CODE,
            segment_count=segment_result.inserted,
            feature_count=feature_count,
            prediction_count=prediction_count,
            final_points=final_rows,
            latest_prediction=latest_prediction,
        )

    def _validate_final_points(self, final_points: list[dict[str, object]]) -> None:
        if not final_points:
            raise ValueError("final_points cannot be empty")
        sorted_points = sorted(final_points, key=lambda row: (row["point_date"], row["point_type"]))
        point_types = [str(row["point_type"]) for row in sorted_points]
        if point_types[0] not in {"trough", "peak"}:
            raise ValueError("invalid point type")
        for previous, current in zip(point_types, point_types[1:], strict=False):
            if previous == current:
                raise ValueError("point types must alternate")

    def _normalize_final_points(
        self,
        *,
        final_points: list[dict[str, object]],
        operations: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        normalized_inputs = [self._normalize_point_row(row) for row in final_points]
        manual_keys = {
            self._point_key(self._normalize_point_row(new_value))
            for operation in operations
            if isinstance(operation.get("new_value"), dict)
            for new_value in [operation["new_value"]]
        }
        merged: list[dict[str, object]] = []
        for point in sorted(normalized_inputs, key=lambda row: (row["point_date"], row["point_type"])):
            if not merged:
                merged.append(point)
                continue
            previous = merged[-1]
            if previous["point_type"] != point["point_type"]:
                merged.append(point)
                continue
            previous_key = self._point_key(previous)
            current_key = self._point_key(point)
            previous_is_manual = previous_key in manual_keys
            current_is_manual = current_key in manual_keys
            if current_is_manual and not previous_is_manual:
                merged[-1] = point
                continue
            if previous_is_manual and not current_is_manual:
                continue
            if self._is_more_extreme(point, previous):
                merged[-1] = point
        return merged

    def _normalize_point_row(self, row: dict[str, object]) -> dict[str, object]:
        point_date = row["point_date"]
        if isinstance(point_date, str):
            point_date = date.fromisoformat(point_date)
        if not isinstance(point_date, date):
            raise ValueError("invalid point_date")
        return {
            "point_date": point_date,
            "point_type": str(row["point_type"]),
            "point_price": float(row["point_price"]),
        }

    def _point_key(self, row: dict[str, object]) -> tuple[date, str, float]:
        return (row["point_date"], str(row["point_type"]), round(float(row["point_price"]), 4))

    def _is_more_extreme(self, current: dict[str, object], previous: dict[str, object]) -> bool:
        current_price = float(current["point_price"])
        previous_price = float(previous["point_price"])
        if str(current["point_type"]) == "peak":
            return current_price >= previous_price
        return current_price <= previous_price

    def _promote_inherited_system_points(
        self,
        *,
        stock_code: str,
        protected_manual_pairs: set[tuple[date, str]],
    ) -> None:
        system_rows = self.session.scalars(
            select(TurningPoint)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.source_type == "system")
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()
        manual_rows = self.session.scalars(
            select(TurningPoint)
            .where(
                TurningPoint.stock_code == stock_code,
                TurningPoint.source_type == "manual",
                TurningPoint.version_code == MANUAL_VERSION_CODE,
                TurningPoint.is_final.is_(True),
            )
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()
        system_rows_by_key: dict[tuple[date, str], list[TurningPoint]] = {}
        for row in system_rows:
            system_rows_by_key.setdefault(self._point_date_type_key_from_model(row), []).append(row)

        for manual_row in manual_rows:
            manual_key = self._point_date_type_key_from_model(manual_row)
            if manual_key in protected_manual_pairs:
                continue
            matches = system_rows_by_key.get(manual_key, [])
            if not matches:
                continue
            inherited_row = matches.pop(0)
            inherited_row.is_final = True
            self.session.delete(manual_row)

    def _point_key_from_model(self, row: TurningPoint) -> tuple[date, str, float]:
        return (row.point_date, row.point_type, round(float(row.point_price), 4))

    def _point_date_type_key(self, row: dict[str, object]) -> tuple[date, str]:
        return (row["point_date"], str(row["point_type"]))

    def _point_date_type_key_from_model(self, row: TurningPoint) -> tuple[date, str]:
        return (row.point_date, row.point_type)
