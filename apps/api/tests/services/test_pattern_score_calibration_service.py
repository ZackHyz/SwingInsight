from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


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


def seed_backtest_rows(session) -> None:
    from swinginsight.db.models.prediction import BacktestResult

    base = date(2022, 1, 1)
    for idx in range(260):
        raw = 0.2 + (idx % 60) / 100
        # intentionally biased labels so calibration has room to correct
        outcome = 1 if raw > 0.65 and idx % 3 == 0 else (1 if raw < 0.35 and idx % 5 == 0 else 0)
        session.add(
            BacktestResult(
                stock_code="600157",
                window_id=idx + 1,
                horizon_days=10,
                query_start_date=base + timedelta(days=idx),
                query_end_date=base + timedelta(days=idx + 6),
                ref_latest_end_date=base + timedelta(days=max(idx - 1, 0)),
                predicted_win_rate=raw,
                predicted_avg_return=raw - 0.5,
                actual_return=0.03 if outcome == 1 else -0.02,
                actual_outcome=outcome,
                sample_count=10,
            )
        )
    session.commit()


def test_calibration_service_fit_and_verify(tmp_path) -> None:
    from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService

    session = build_session()
    seed_backtest_rows(session)
    service = PatternScoreCalibrationService(session, calibration_dir=tmp_path / "calibration")

    report = service.fit(stock_code="600157", horizon_days=10, method="isotonic", train_ratio=0.7, min_sample_count=5)
    assert report["train_size"] > 0
    assert report["val_size"] > 0
    assert Path(report["model_path"]).exists()
    assert 0.0 <= report["brier_before"] <= 1.0
    assert 0.0 <= report["brier_after"] <= 1.0

    verify = service.verify(stock_code="600157", horizon_days=10, method="isotonic", train_ratio=0.7, min_sample_count=5)
    assert verify["val_size"] > 0
    assert len(verify["curve_rows"]) == 10


def test_calibration_service_predict_fallback_and_calibrated(tmp_path) -> None:
    from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService

    session = build_session()
    seed_backtest_rows(session)
    service = PatternScoreCalibrationService(session, calibration_dir=tmp_path / "calibration")

    raw_only = service.predict(stock_code="600157", raw_score=0.62, horizon_days=10, method="platt")
    assert raw_only == 0.62

    service.fit(stock_code="600157", horizon_days=10, method="platt", train_ratio=0.7, min_sample_count=5)
    calibrated = service.predict(stock_code="600157", raw_score=0.62, horizon_days=10, method="platt")
    assert 0.0 <= calibrated <= 1.0
