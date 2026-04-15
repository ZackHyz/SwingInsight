from __future__ import annotations

from datetime import date
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


def test_feature_signal_diagnosis_returns_ranked_rows() -> None:
    from swinginsight.db.models.pattern import PatternFeature
    from swinginsight.db.models.prediction import BacktestResult
    from swinginsight.services.feature_signal_diagnosis_service import FeatureSignalDiagnosisService

    session = build_session()
    for idx in range(20):
        window_id = idx + 1
        session.add(
            PatternFeature(
                window_id=window_id,
                coarse_vector_json=[float(idx), 1.0 if idx % 2 == 0 else 0.0] + [0.0] * 19,
                context_feature_json={"vol_ratio_vs_ma20": float(idx) / 10.0},
                price_seq_json=[1.0] * 7,
                candle_feat_json=[0.0] * 35,
                volume_seq_json=[1.0] * 7,
                turnover_seq_json=[1.0] * 7,
                trend_context_json=[0.0],
                vola_context_json=[0.0],
                feature_version="pattern:v1",
            )
        )
        outcome = 1 if idx >= 10 else 0
        session.add(
            BacktestResult(
                stock_code="600157",
                window_id=window_id,
                horizon_days=5,
                query_start_date=date(2024, 1, 1),
                query_end_date=date(2024, 1, 7),
                ref_latest_end_date=date(2023, 12, 31),
                predicted_win_rate=0.5,
                predicted_avg_return=0.0,
                actual_return=0.03 if outcome == 1 else -0.03,
                actual_outcome=outcome,
                sample_count=10,
            )
        )
    session.commit()

    result = FeatureSignalDiagnosisService(session).diagnose(stock_code="600157", horizon_days=5, min_sample_count=5)
    assert result["rows"]
    top_row = result["rows"][0]
    assert top_row.n == 20
    assert abs(top_row.r_outcome) > 0.2


def test_feature_signal_diagnosis_rejects_unknown_feature_name() -> None:
    import pytest

    from swinginsight.services.feature_signal_diagnosis_service import FeatureSignalDiagnosisService

    session = build_session()
    with pytest.raises(ValueError):
        FeatureSignalDiagnosisService(session).diagnose(
            stock_code="600157",
            horizon_days=5,
            min_sample_count=5,
            feature_names=["unknown_feature"],
        )
