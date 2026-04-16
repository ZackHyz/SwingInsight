from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from statistics import median
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.prediction import BacktestResult
from swinginsight.db.models.turning_point import TurningPoint
from swinginsight.services.pattern_score_backtest_service import PatternScoreBacktestService
from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService


@dataclass(slots=True, frozen=True)
class TurningPointMetrics:
    final_count: int
    system_count: int
    exact_match_precision: float
    exact_match_recall: float
    f1_exact: float
    tolerance_match_recall_2d: float
    median_confirm_lag_days: int | None

    def as_dict(self) -> dict[str, int | float | None]:
        return {
            "final_count": self.final_count,
            "system_count": self.system_count,
            "exact_match_precision": self.exact_match_precision,
            "exact_match_recall": self.exact_match_recall,
            "f1_exact": self.f1_exact,
            "tolerance_match_recall_2d": self.tolerance_match_recall_2d,
            "median_confirm_lag_days": self.median_confirm_lag_days,
        }


class BatchEvaluationService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def evaluate_turning_points(self, stock_code: str) -> dict[str, int | float | None]:
        final_points = self.session.scalars(
            select(TurningPoint)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.is_final.is_(True))
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()
        system_points = self.session.scalars(
            select(TurningPoint)
            .where(TurningPoint.stock_code == stock_code, TurningPoint.source_type == "system")
            .order_by(TurningPoint.point_date.asc(), TurningPoint.id.asc())
        ).all()

        final_count = len(final_points)
        system_count = len(system_points)
        final_exact_pairs = {(point.point_date, point.point_type) for point in final_points}
        system_exact_pairs = {(point.point_date, point.point_type) for point in system_points}
        exact_hits = len(final_exact_pairs & system_exact_pairs)

        precision = exact_hits / system_count if system_count else 0.0
        recall = exact_hits / final_count if final_count else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if precision and recall else 0.0

        tolerance_hits = 0
        for final_point in final_points:
            if self._has_tolerance_match(final_point_date=final_point.point_date, final_point_type=final_point.point_type, system_points=system_points):
                tolerance_hits += 1
        tolerance_recall = tolerance_hits / final_count if final_count else 0.0

        lags = [
            (point.confirm_date - point.point_date).days
            for point in system_points
            if point.confirm_date is not None
        ]
        median_confirm_lag_days = int(median(lags)) if lags else None

        return TurningPointMetrics(
            final_count=final_count,
            system_count=system_count,
            exact_match_precision=round(precision, 4),
            exact_match_recall=round(recall, 4),
            f1_exact=round(f1, 4),
            tolerance_match_recall_2d=round(tolerance_recall, 4),
            median_confirm_lag_days=median_confirm_lag_days,
        ).as_dict()

    def evaluate_stock(
        self,
        *,
        stock_code: str,
        start: date,
        end: date,
        horizons: list[int],
    ) -> dict[str, object]:
        turning_point_metrics = self.evaluate_turning_points(stock_code)
        pattern: dict[int, dict[str, object]] = {}
        calibration: dict[int, dict[str, object]] = {}
        for horizon in horizons:
            pattern[horizon] = self._evaluate_pattern_for_horizon(stock_code, horizon, start, end)
            calibration[horizon] = self._evaluate_calibration_for_horizon(stock_code, horizon)
        return {
            "stock_code": stock_code,
            "turning_points": turning_point_metrics,
            "pattern": pattern,
            "calibration": calibration,
        }

    def rank_categories(self, category_summary: dict[str, dict[str, float]]) -> list[dict[str, object]]:
        weighted: list[tuple[str, float]] = []
        for category, summary in category_summary.items():
            coverage = float(summary.get("coverage_rate", 0.0))
            brier = float(summary.get("brier_after", 1.0))
            f1_exact = float(summary.get("f1_exact", 0.0))
            score = 0.4 * coverage + 0.35 * max(0.0, 1.0 - brier) + 0.25 * f1_exact
            weighted.append((category, score))
        weighted.sort(key=lambda row: row[1], reverse=True)
        return [
            {"category": category, "score": round(score, 4), "reliability_rank": index + 1}
            for index, (category, score) in enumerate(weighted)
        ]

    def evaluate_batch(
        self,
        *,
        sample_pool: dict[str, list[dict[str, str]]],
        start: date,
        end: date,
        horizons: list[int],
    ) -> dict[str, Any]:
        categories_payload: dict[str, dict[str, Any]] = {}
        ranking_input: dict[str, dict[str, float]] = {}
        total_success = 0
        failures: list[dict[str, str]] = []

        for category, stocks in sample_pool.items():
            stock_reports: list[dict[str, object]] = []
            for stock in stocks:
                stock_code = stock["stock_code"]
                try:
                    stock_report = self.evaluate_stock(
                        stock_code=stock_code,
                        start=start,
                        end=end,
                        horizons=horizons,
                    )
                    stock_reports.append(stock_report)
                    total_success += 1
                except Exception as exc:  # noqa: BLE001
                    failures.append({"category": category, "stock_code": stock_code, "error": str(exc)})
            category_summary = self._aggregate_category(stock_reports=stock_reports, horizons=horizons)
            ranking_input[category] = {
                "coverage_rate": float(category_summary["coverage_rate"]),
                "brier_after": float(category_summary["brier_after"]),
                "f1_exact": float(category_summary["f1_exact"]),
            }
            categories_payload[category] = {
                "stocks": stock_reports,
                "summary": category_summary,
            }

        ranked = self.rank_categories(ranking_input)
        return {
            "categories": categories_payload,
            "ranked_categories": ranked,
            "failures": failures,
            "total_success": total_success,
        }

    def _evaluate_pattern_for_horizon(
        self,
        stock_code: str,
        horizon: int,
        start: date,
        end: date,
    ) -> dict[str, object]:
        backtest_service = PatternScoreBacktestService(self.session)
        run_result = backtest_service.run_backtest(
            stock_code=stock_code,
            start=start,
            end=end,
            horizon_days=[horizon],
            top_k=20,
            min_reference_size=10,
            min_similarity=0.70,
            min_samples=5,
        )
        self.session.flush()
        summary = backtest_service.summarize(
            stock_code=stock_code,
            horizon=horizon,
            min_sample_count=5,
            processed_queries=int(run_result["processed_queries"]),
        )
        rows = self.session.scalars(
            select(BacktestResult).where(
                BacktestResult.stock_code == stock_code,
                BacktestResult.horizon_days == horizon,
                BacktestResult.actual_outcome.is_not(None),
            )
        ).all()
        if rows:
            win_rate_observed = sum(int(row.actual_outcome or 0) for row in rows) / len(rows)
            avg_predicted = sum(float(row.predicted_win_rate) for row in rows) / len(rows)
        else:
            win_rate_observed = 0.0
            avg_predicted = 0.0
        return {
            **summary,
            "horizon": horizon,
            "win_rate_observed": round(win_rate_observed, 4),
            "avg_predicted_win_rate": round(avg_predicted, 4),
            "calibration_gap": round(abs(avg_predicted - win_rate_observed), 4),
        }

    def _evaluate_calibration_for_horizon(self, stock_code: str, horizon: int) -> dict[str, object]:
        calibration_service = PatternScoreCalibrationService(self.session)
        try:
            calibration_service.fit(
                stock_code=stock_code,
                horizon_days=horizon,
                method="isotonic",
                train_ratio=0.7,
                min_sample_count=5,
            )
            verify = calibration_service.verify(
                stock_code=stock_code,
                horizon_days=horizon,
                method="isotonic",
                train_ratio=0.7,
                min_sample_count=5,
            )
        except ValueError as exc:
            return {
                "horizon": horizon,
                "brier_before": 0.0,
                "brier_after": 0.0,
                "delta_brier": 0.0,
                "is_monotonic": False,
                "mean_abs_bucket_error_before": 0.0,
                "mean_abs_bucket_error_after": 0.0,
                "bucket_error_delta": 0.0,
                "error": str(exc),
            }

        curve_rows = [row for row in verify.get("curve_rows", []) if int(row.get("n", 0)) > 0]
        if curve_rows:
            before_errors = [abs(float(row["raw_mean"]) - float(row["actual_mean"])) for row in curve_rows]
            after_errors = [abs(float(row["cal_mean"]) - float(row["actual_mean"])) for row in curve_rows]
            mean_before = sum(before_errors) / len(before_errors)
            mean_after = sum(after_errors) / len(after_errors)
        else:
            mean_before = 0.0
            mean_after = 0.0

        brier_before = float(verify.get("brier_before", 0.0))
        brier_after = float(verify.get("brier_after", 0.0))
        return {
            "horizon": horizon,
            "brier_before": round(brier_before, 4),
            "brier_after": round(brier_after, 4),
            "delta_brier": round(brier_after - brier_before, 4),
            "is_monotonic": bool(verify.get("is_monotonic", False)),
            "mean_abs_bucket_error_before": round(mean_before, 4),
            "mean_abs_bucket_error_after": round(mean_after, 4),
            "bucket_error_delta": round(mean_after - mean_before, 4),
        }

    def _aggregate_category(self, *, stock_reports: list[dict[str, object]], horizons: list[int]) -> dict[str, float]:
        if not stock_reports:
            return {"coverage_rate": 0.0, "brier_after": 1.0, "f1_exact": 0.0}

        coverage_values: list[float] = []
        brier_after_values: list[float] = []
        f1_values: list[float] = []
        for stock_report in stock_reports:
            turning = stock_report["turning_points"]
            f1_values.append(float(turning["f1_exact"]))
            pattern = stock_report["pattern"]
            calibration = stock_report["calibration"]
            for horizon in horizons:
                coverage_values.append(float(pattern[horizon]["coverage_rate"]))
                brier_after_values.append(float(calibration[horizon]["brier_after"]))
        coverage = sum(coverage_values) / len(coverage_values) if coverage_values else 0.0
        brier_after = sum(brier_after_values) / len(brier_after_values) if brier_after_values else 1.0
        f1_exact = sum(f1_values) / len(f1_values) if f1_values else 0.0
        return {
            "coverage_rate": round(coverage, 4),
            "brier_after": round(brier_after, 4),
            "f1_exact": round(f1_exact, 4),
        }

    def _has_tolerance_match(
        self,
        *,
        final_point_date: date,
        final_point_type: str,
        system_points: list[TurningPoint],
    ) -> bool:
        for point in system_points:
            if point.point_type != final_point_type:
                continue
            delta_days = abs((point.point_date - final_point_date).days)
            if delta_days <= 2:
                return True
        return False
