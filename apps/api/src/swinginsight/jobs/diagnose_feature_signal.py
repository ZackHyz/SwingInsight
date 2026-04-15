from __future__ import annotations

from dataclasses import dataclass

from swinginsight.db.session import session_scope
from swinginsight.services.feature_signal_diagnosis_service import FeatureSignalDiagnosisService, FeatureSignalRow


@dataclass(slots=True, frozen=True)
class DiagnoseFeatureSignalResult:
    stock_code: str
    horizon_days: int
    strong_signal_count: int
    strong_features: list[str]
    rows: list[FeatureSignalRow]


def diagnose_feature_signal(
    *,
    stock_code: str,
    horizon_days: int = 5,
    min_sample_count: int = 5,
    feature_names: list[str] | None = None,
) -> DiagnoseFeatureSignalResult:
    with session_scope() as session:
        payload = FeatureSignalDiagnosisService(session).diagnose(
            stock_code=stock_code,
            horizon_days=horizon_days,
            min_sample_count=min_sample_count,
            feature_names=feature_names,
        )
    return DiagnoseFeatureSignalResult(
        stock_code=stock_code,
        horizon_days=horizon_days,
        strong_signal_count=int(payload["strong_signal_count"]),
        strong_features=list(payload["strong_features"]),
        rows=list(payload["rows"]),
    )
