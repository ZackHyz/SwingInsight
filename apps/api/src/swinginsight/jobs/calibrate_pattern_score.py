from __future__ import annotations

from dataclasses import dataclass

from swinginsight.db.session import session_scope
from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService


@dataclass(slots=True, frozen=True)
class CalibratePatternScoreResult:
    reports: list[dict[str, object]]


def calibrate_pattern_score(
    *,
    stock_code: str,
    horizon_days: list[int],
    method: str,
    train_ratio: float = 0.7,
    min_sample_count: int = 5,
) -> CalibratePatternScoreResult:
    reports: list[dict[str, object]] = []
    with session_scope() as session:
        service = PatternScoreCalibrationService(session)
        for horizon in horizon_days:
            reports.append(
                service.fit(
                    stock_code=stock_code,
                    horizon_days=horizon,
                    method=method,
                    train_ratio=train_ratio,
                    min_sample_count=min_sample_count,
                )
            )
    return CalibratePatternScoreResult(reports=reports)


def verify_calibration(
    *,
    stock_code: str,
    horizon_days: int,
    method: str,
    train_ratio: float = 0.7,
    min_sample_count: int = 5,
) -> dict[str, object]:
    with session_scope() as session:
        service = PatternScoreCalibrationService(session)
        return service.verify(
            stock_code=stock_code,
            horizon_days=horizon_days,
            method=method,
            train_ratio=train_ratio,
            min_sample_count=min_sample_count,
        )
