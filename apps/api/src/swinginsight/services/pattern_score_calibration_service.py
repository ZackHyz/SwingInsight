from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import pickle
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.prediction import BacktestResult


@dataclass(slots=True, frozen=True)
class CalibrationBucketRow:
    bucket: str
    n: int
    raw_mean: float
    cal_mean: float
    actual: float
    error_before: float
    error_after: float


class PatternScoreCalibrationService:
    def __init__(self, session: Session, calibration_dir: Path | None = None) -> None:
        self.session = session
        self.calibration_dir = calibration_dir or (Path(__file__).resolve().parents[3] / "data" / "calibration")

    def fit(
        self,
        *,
        stock_code: str,
        horizon_days: int,
        method: str = "isotonic",
        train_ratio: float = 0.7,
        min_sample_count: int = 5,
    ) -> dict[str, object]:
        raw_scores, outcomes = self._load_series(
            stock_code=stock_code,
            horizon_days=horizon_days,
            min_sample_count=min_sample_count,
        )
        if len(raw_scores) < 50:
            raise ValueError(f"Not enough backtest rows for calibration: {len(raw_scores)}")
        split = max(int(len(raw_scores) * train_ratio), 1)
        split = min(split, len(raw_scores) - 1)
        x_train, y_train = raw_scores[:split], outcomes[:split]
        x_val, y_val = raw_scores[split:], outcomes[split:]

        model: dict[str, object]
        if method == "isotonic":
            model = self._fit_isotonic(x_train, y_train)
        elif method == "platt":
            model = self._fit_platt(x_train, y_train)
        else:
            raise ValueError(f"Unsupported calibration method: {method}")

        y_cal = self._predict_array(model, x_val)
        buckets = self._bucket_error(raw=x_val, calibrated=y_cal, actual=y_val)
        brier_before = self._brier(raw=x_val, actual=y_val)
        brier_after = self._brier(raw=y_cal, actual=y_val)

        payload = {
            "method": method,
            "horizon_days": horizon_days,
            "stock_code": stock_code,
            "trained_at": datetime.now(UTC).isoformat(),
            "train_ratio": train_ratio,
            "model": model,
        }
        path = self._model_path(stock_code=stock_code, horizon_days=horizon_days, method=method)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as fp:
            pickle.dump(payload, fp)

        return {
            "method": method,
            "horizon_days": horizon_days,
            "stock_code": stock_code,
            "train_size": len(x_train),
            "val_size": len(x_val),
            "brier_before": round(brier_before, 4),
            "brier_after": round(brier_after, 4),
            "bucket_metrics": buckets,
            "model_path": str(path),
        }

    def predict(self, *, stock_code: str, raw_score: float, horizon_days: int, method: str = "isotonic") -> float:
        calibrated, _ = self.predict_with_meta(
            stock_code=stock_code,
            raw_score=raw_score,
            horizon_days=horizon_days,
            method=method,
        )
        return calibrated

    def predict_with_meta(
        self,
        *,
        stock_code: str,
        raw_score: float,
        horizon_days: int,
        method: str = "isotonic",
    ) -> tuple[float, bool]:
        payload = self._load_model(stock_code=stock_code, horizon_days=horizon_days, method=method)
        if payload is None:
            return float(raw_score), False
        model = payload["model"]
        calibrated = float(self._predict_array(model, np.array([raw_score], dtype=np.float64))[0])
        return calibrated, True

    def verify(
        self,
        *,
        stock_code: str,
        horizon_days: int,
        method: str = "isotonic",
        train_ratio: float = 0.7,
        min_sample_count: int = 5,
    ) -> dict[str, object]:
        payload = self._load_model(stock_code=stock_code, horizon_days=horizon_days, method=method)
        if payload is None:
            raise ValueError("Calibration model not found; run calibrate-pattern-score first")
        raw_scores, outcomes = self._load_series(
            stock_code=stock_code,
            horizon_days=horizon_days,
            min_sample_count=min_sample_count,
        )
        split = max(int(len(raw_scores) * train_ratio), 1)
        split = min(split, len(raw_scores) - 1)
        x_val, y_val = raw_scores[split:], outcomes[split:]
        y_cal = self._predict_array(payload["model"], x_val)
        curve_rows = self._calibration_curve_rows(raw=x_val, calibrated=y_cal, actual=y_val, bins=10)
        cal_means = [row["cal_mean"] for row in curve_rows if row["n"] > 0]
        is_monotonic = all(a <= b + 1e-12 for a, b in zip(cal_means, cal_means[1:], strict=False))
        return {
            "stock_code": stock_code,
            "horizon_days": horizon_days,
            "method": method,
            "val_size": len(x_val),
            "brier_before": round(self._brier(raw=x_val, actual=y_val), 4),
            "brier_after": round(self._brier(raw=y_cal, actual=y_val), 4),
            "is_monotonic": is_monotonic,
            "curve_rows": curve_rows,
        }

    def _load_series(self, *, stock_code: str, horizon_days: int, min_sample_count: int) -> tuple[np.ndarray, np.ndarray]:
        rows = self.session.execute(
            select(BacktestResult.predicted_win_rate, BacktestResult.actual_outcome)
            .where(
                BacktestResult.stock_code == stock_code,
                BacktestResult.horizon_days == horizon_days,
                BacktestResult.sample_count >= min_sample_count,
                BacktestResult.actual_outcome.is_not(None),
                BacktestResult.predicted_win_rate.is_not(None),
            )
            .order_by(BacktestResult.query_end_date.asc(), BacktestResult.id.asc())
        ).all()
        raw = np.array([float(row[0]) for row in rows], dtype=np.float64)
        y = np.array([float(row[1]) for row in rows], dtype=np.float64)
        return raw, y

    def _fit_isotonic(self, x: np.ndarray, y: np.ndarray) -> dict[str, object]:
        order = np.argsort(x)
        xs = x[order]
        ys = y[order]

        blocks: list[dict[str, float]] = []
        for x_val, y_val in zip(xs, ys, strict=False):
            blocks.append({"sum_y": float(y_val), "count": 1.0, "x_max": float(x_val)})
            while len(blocks) >= 2:
                left = blocks[-2]
                right = blocks[-1]
                left_mean = left["sum_y"] / left["count"]
                right_mean = right["sum_y"] / right["count"]
                if left_mean <= right_mean:
                    break
                merged = {
                    "sum_y": left["sum_y"] + right["sum_y"],
                    "count": left["count"] + right["count"],
                    "x_max": right["x_max"],
                }
                blocks = blocks[:-2] + [merged]

        thresholds = np.array([block["x_max"] for block in blocks], dtype=np.float64)
        values = np.array([block["sum_y"] / block["count"] for block in blocks], dtype=np.float64)
        return {"type": "isotonic", "thresholds": thresholds, "values": values}

    def _fit_platt(self, x: np.ndarray, y: np.ndarray) -> dict[str, object]:
        mean = float(np.mean(x))
        std = float(np.std(x))
        std = std if std > 1e-12 else 1.0
        z = (x - mean) / std
        a = 0.0
        b = 0.0
        lr = 0.05
        l2 = 1e-3
        n = max(len(z), 1)
        for _ in range(4000):
            logits = np.clip(a * z + b, -30.0, 30.0)
            p = 1.0 / (1.0 + np.exp(-logits))
            da = float(np.sum((p - y) * z) / n + l2 * a)
            db = float(np.sum(p - y) / n)
            a -= lr * da
            b -= lr * db
        return {"type": "platt", "mean": mean, "std": std, "a": a, "b": b}

    def _predict_array(self, model: dict[str, object], raw_scores: np.ndarray) -> np.ndarray:
        if model["type"] == "isotonic":
            thresholds = np.array(model["thresholds"], dtype=np.float64)
            values = np.array(model["values"], dtype=np.float64)
            indices = np.searchsorted(thresholds, raw_scores, side="left")
            indices = np.clip(indices, 0, len(values) - 1)
            return values[indices]
        z = (raw_scores - float(model["mean"])) / float(model["std"])
        logits = np.clip(float(model["a"]) * z + float(model["b"]), -30.0, 30.0)
        return 1.0 / (1.0 + np.exp(-logits))

    def _bucket_error(self, *, raw: np.ndarray, calibrated: np.ndarray, actual: np.ndarray, n_buckets: int = 5) -> list[CalibrationBucketRow]:
        edges = np.linspace(0.0, 1.0, n_buckets + 1)
        rows: list[CalibrationBucketRow] = []
        for idx in range(n_buckets):
            lo = edges[idx]
            hi = edges[idx + 1]
            if idx == n_buckets - 1:
                mask = (raw >= lo) & (raw <= hi)
            else:
                mask = (raw >= lo) & (raw < hi)
            if int(mask.sum()) < 3:
                continue
            raw_mean = float(np.mean(raw[mask]))
            cal_mean = float(np.mean(calibrated[mask]))
            actual_mean = float(np.mean(actual[mask]))
            rows.append(
                CalibrationBucketRow(
                    bucket=f"{lo:.1f}-{hi:.1f}",
                    n=int(mask.sum()),
                    raw_mean=round(raw_mean, 4),
                    cal_mean=round(cal_mean, 4),
                    actual=round(actual_mean, 4),
                    error_before=round(abs(raw_mean - actual_mean), 4),
                    error_after=round(abs(cal_mean - actual_mean), 4),
                )
            )
        return rows

    def _calibration_curve_rows(self, *, raw: np.ndarray, calibrated: np.ndarray, actual: np.ndarray, bins: int) -> list[dict[str, object]]:
        edges = np.linspace(0.0, 1.0, bins + 1)
        rows: list[dict[str, object]] = []
        for idx in range(bins):
            lo = float(edges[idx])
            hi = float(edges[idx + 1])
            mask = (raw >= lo) & (raw < hi) if idx < bins - 1 else (raw >= lo) & (raw <= hi)
            n = int(mask.sum())
            rows.append(
                {
                    "bucket": f"{lo:.1f}-{hi:.1f}",
                    "n": n,
                    "raw_mean": round(float(np.mean(raw[mask])), 4) if n else 0.0,
                    "cal_mean": round(float(np.mean(calibrated[mask])), 4) if n else 0.0,
                    "actual_mean": round(float(np.mean(actual[mask])), 4) if n else 0.0,
                }
            )
        return rows

    def _brier(self, *, raw: np.ndarray, actual: np.ndarray) -> float:
        if len(raw) == 0:
            return 0.0
        return float(np.mean((raw - actual) ** 2))

    def _model_path(self, *, stock_code: str, horizon_days: int, method: str) -> Path:
        return self.calibration_dir / f"{stock_code}_{horizon_days}d_{method}.pkl"

    def _load_model(self, *, stock_code: str, horizon_days: int, method: str) -> dict[str, object] | None:
        path = self._model_path(stock_code=stock_code, horizon_days=horizon_days, method=method)
        if not path.exists():
            return None
        with path.open("rb") as fp:
            return pickle.load(fp)
