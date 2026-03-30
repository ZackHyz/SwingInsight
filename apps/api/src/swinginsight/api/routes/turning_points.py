from __future__ import annotations

from swinginsight.api.schemas.turning_points import TurningPointCommitRequest
from swinginsight.services.manual_turning_point_service import ManualTurningPointService


def commit_turning_points(*, stock_code: str, payload: TurningPointCommitRequest, session) -> dict[str, object]:
    result = ManualTurningPointService(session).commit_final_points(
        stock_code=stock_code,
        operator=payload.operator,
        final_points=[
            {"point_date": row.point_date, "point_type": row.point_type, "point_price": row.point_price}
            for row in payload.final_points
        ],
        operations=[
            {
                "operation_type": row.operation_type,
                "old_value": row.old_value,
                "new_value": row.new_value,
            }
            for row in payload.operations
        ],
    )
    return {
        "final_turning_points": [
            {
                "id": row.id,
                "point_date": row.point_date.isoformat(),
                "point_type": row.point_type,
                "point_price": float(row.point_price),
                "source_type": row.source_type,
            }
            for row in result.final_points
        ],
        "rebuild_summary": {
            "segments": result.segment_count,
            "version_code": result.version_code,
        },
    }
