from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from swinginsight.db.models.segment import SwingSegment
from swinginsight.db.models.turning_point import PointRevisionLog, TurningPoint
from swinginsight.services.segment_generation_service import SegmentGenerationService


MANUAL_VERSION_CODE = "manual:latest"


@dataclass(slots=True, frozen=True)
class ManualTurningPointCommitResult:
    version_code: str
    segment_count: int
    final_points: list[TurningPoint]


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
        self._validate_final_points(final_points)

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
        segment_result = SegmentGenerationService(self.session).rebuild_segments(
            stock_code=stock_code,
            version_code=MANUAL_VERSION_CODE,
        )
        final_rows = self.session.scalars(
            select(TurningPoint)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()
        return ManualTurningPointCommitResult(
            version_code=MANUAL_VERSION_CODE,
            segment_count=segment_result.inserted,
            final_points=final_rows,
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
