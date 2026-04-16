from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_session():
    from swinginsight.db.base import Base
    from swinginsight.db import models as _models  # noqa: F401

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()


def test_turning_point_metrics_compute_exact_and_tolerance_recall() -> None:
    from swinginsight.db.models.turning_point import TurningPoint
    from swinginsight.services.batch_evaluation_service import BatchEvaluationService

    session = build_session()
    stock_code = "600001"

    session.add_all(
        [
            TurningPoint(
                stock_code=stock_code,
                point_date=date(2024, 1, 5),
                point_type="peak",
                point_price=12.0,
                confirm_date=date(2024, 1, 7),
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code=stock_code,
                point_date=date(2024, 1, 10),
                point_type="trough",
                point_price=10.0,
                confirm_date=date(2024, 1, 12),
                source_type="system",
                version_code="zigzag:test",
                is_final=False,
            ),
            TurningPoint(
                stock_code=stock_code,
                point_date=date(2024, 1, 5),
                point_type="peak",
                point_price=12.1,
                confirm_date=None,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
            TurningPoint(
                stock_code=stock_code,
                point_date=date(2024, 1, 11),
                point_type="trough",
                point_price=9.9,
                confirm_date=None,
                source_type="manual",
                version_code="manual:latest",
                is_final=True,
            ),
        ]
    )
    session.commit()

    metrics = BatchEvaluationService(session).evaluate_turning_points(stock_code)
    assert metrics["final_count"] == 2
    assert metrics["system_count"] == 2
    assert metrics["f1_exact"] >= 0.0
    assert metrics["tolerance_match_recall_2d"] >= metrics["exact_match_recall"]
    assert metrics["median_confirm_lag_days"] == 2


def test_pattern_and_calibration_metrics_include_horizons(monkeypatch) -> None:
    from swinginsight.services.batch_evaluation_service import BatchEvaluationService

    session = build_session()
    service = BatchEvaluationService(session)

    monkeypatch.setattr(
        service,
        "_evaluate_pattern_for_horizon",
        lambda stock_code, horizon, start, end: {
            "horizon": horizon,
            "rows": 20,
            "coverage_rate": 0.8,
            "brier_score": 0.22,
            "win_rate_observed": 0.6,
            "avg_predicted_win_rate": 0.58,
            "calibration_gap": 0.02,
            "sample_count_distribution": {"<5": 0, "5-9": 3, "10-19": 9, "20-29": 8, "30+": 0},
            "tiers": [],
        },
    )
    monkeypatch.setattr(
        service,
        "_evaluate_calibration_for_horizon",
        lambda stock_code, horizon: {
            "horizon": horizon,
            "brier_before": 0.24,
            "brier_after": 0.21,
            "delta_brier": -0.03,
            "is_monotonic": True,
            "mean_abs_bucket_error_before": 0.12,
            "mean_abs_bucket_error_after": 0.09,
            "bucket_error_delta": -0.03,
        },
    )
    monkeypatch.setattr(
        service,
        "evaluate_turning_points",
        lambda stock_code: {
            "final_count": 2,
            "system_count": 2,
            "exact_match_precision": 0.5,
            "exact_match_recall": 0.5,
            "f1_exact": 0.5,
            "tolerance_match_recall_2d": 1.0,
            "median_confirm_lag_days": 2,
        },
    )

    result = service.evaluate_stock(
        stock_code="600001",
        start=date(2022, 1, 1),
        end=date(2025, 12, 31),
        horizons=[5, 10, 20],
    )

    assert result["stock_code"] == "600001"
    assert set(result["pattern"].keys()) == {5, 10, 20}
    assert set(result["calibration"].keys()) == {5, 10, 20}


def test_rank_categories_assigns_order_by_weighted_score() -> None:
    from swinginsight.services.batch_evaluation_service import BatchEvaluationService

    service = BatchEvaluationService(build_session())
    ranked = service.rank_categories(
        {
            "trend_names": {"coverage_rate": 0.8, "brier_after": 0.18, "f1_exact": 0.7},
            "range_names": {"coverage_rate": 0.5, "brier_after": 0.22, "f1_exact": 0.5},
            "low_liquidity_names": {"coverage_rate": 0.3, "brier_after": 0.30, "f1_exact": 0.3},
        }
    )
    assert ranked[0]["category"] == "trend_names"
    assert ranked[-1]["category"] == "low_liquidity_names"
    assert {row["reliability_rank"] for row in ranked} == {1, 2, 3}
