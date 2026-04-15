from __future__ import annotations

from dataclasses import dataclass
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.pattern import PatternFeature
from swinginsight.db.models.prediction import BacktestResult
from swinginsight.services.feature_catalog import ALL_FEATURE_NAMES


@dataclass(slots=True, frozen=True)
class FeatureSignalRow:
    feature: str
    r_outcome: float
    r_return: float
    p_outcome: float
    n: int


class FeatureSignalDiagnosisService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def diagnose(
        self,
        *,
        stock_code: str,
        horizon_days: int = 5,
        min_sample_count: int = 5,
        feature_names: list[str] | None = None,
    ) -> dict[str, object]:
        pairs = self._load_pairs(stock_code=stock_code, horizon_days=horizon_days, min_sample_count=min_sample_count)
        target_features = feature_names if feature_names else list(ALL_FEATURE_NAMES)
        invalid = [name for name in target_features if name not in ALL_FEATURE_NAMES]
        if invalid:
            raise ValueError(f"Unknown feature names: {invalid}")
        rows: list[FeatureSignalRow] = []
        for feature_name in target_features:
            triples = [
                (feature_map[feature_name], outcome, ret)
                for feature_map, outcome, ret in pairs
                if feature_name in feature_map
            ]
            if len(triples) < 8:
                continue
            xs = [item[0] for item in triples]
            ys_outcome = [item[1] for item in triples]
            ys_return = [item[2] for item in triples]
            r_outcome = self._pearson(xs, ys_outcome)
            r_return = self._pearson(xs, ys_return)
            rows.append(
                FeatureSignalRow(
                    feature=feature_name,
                    r_outcome=round(r_outcome, 4),
                    r_return=round(r_return, 4),
                    p_outcome=round(self._approx_p_value(r_outcome, len(xs)), 4),
                    n=len(xs),
                )
            )
        rows.sort(key=lambda item: abs(item.r_outcome), reverse=True)
        strong = [row for row in rows if abs(row.r_outcome) >= 0.08 and row.p_outcome <= 0.05]
        return {
            "stock_code": stock_code,
            "horizon_days": horizon_days,
            "rows": rows,
            "strong_signal_count": len(strong),
            "strong_features": [row.feature for row in strong],
        }

    def _load_pairs(
        self,
        *,
        stock_code: str,
        horizon_days: int,
        min_sample_count: int,
    ) -> list[tuple[dict[str, float], float, float]]:
        rows = self.session.execute(
            select(
                PatternFeature.coarse_vector_json,
                PatternFeature.context_feature_json,
                BacktestResult.actual_outcome,
                BacktestResult.actual_return,
            )
            .join(BacktestResult, BacktestResult.window_id == PatternFeature.window_id)
            .where(
                BacktestResult.stock_code == stock_code,
                BacktestResult.horizon_days == horizon_days,
                BacktestResult.sample_count >= min_sample_count,
                BacktestResult.actual_outcome.is_not(None),
                BacktestResult.actual_return.is_not(None),
            )
            .order_by(BacktestResult.id.asc())
        ).all()
        pairs: list[tuple[dict[str, float], float, float]] = []
        for vector, context_feature_json, outcome, actual_return in rows:
            if not vector and not context_feature_json:
                continue
            payload: dict[str, float] = {}
            for idx, value in enumerate(list(vector or [])):
                if idx >= len(ALL_FEATURE_NAMES):
                    break
                payload[ALL_FEATURE_NAMES[idx]] = float(value)
            for key, value in (context_feature_json or {}).items():
                if key in ALL_FEATURE_NAMES:
                    try:
                        payload[key] = float(value)
                    except (TypeError, ValueError):
                        continue
            pairs.append(
                (
                    payload,
                    float(outcome),
                    float(actual_return),
                )
            )
        return pairs

    def _pearson(self, xs: list[float], ys: list[float]) -> float:
        if len(xs) != len(ys) or len(xs) < 2:
            return 0.0
        mean_x = sum(xs) / len(xs)
        mean_y = sum(ys) / len(ys)
        cov = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=False))
        var_x = sum((x - mean_x) ** 2 for x in xs)
        var_y = sum((y - mean_y) ** 2 for y in ys)
        denom = (var_x * var_y) ** 0.5
        if denom == 0:
            return 0.0
        return max(min(cov / denom, 1.0), -1.0)

    def _approx_p_value(self, r: float, n: int) -> float:
        if n < 4:
            return 1.0
        r = max(min(r, 0.999999), -0.999999)
        fisher_z = 0.5 * math.log((1 + r) / (1 - r)) * math.sqrt(max(n - 3, 1))
        p = 2 * (1 - self._normal_cdf(abs(fisher_z)))
        return max(0.0, min(1.0, p))

    def _normal_cdf(self, value: float) -> float:
        return 0.5 * (1 + math.erf(value / math.sqrt(2)))
