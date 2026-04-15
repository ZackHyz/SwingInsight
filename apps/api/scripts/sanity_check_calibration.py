from __future__ import annotations

from pathlib import Path
import sys

from sqlalchemy.orm import Session

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swinginsight.db.session import SessionLocal
from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService


def main() -> None:
    stock_code = sys.argv[1] if len(sys.argv) > 1 else "600157"
    raw_scores = [0.3, 0.4, 0.5, 0.55, 0.6, 0.65, 0.7, 0.75, 0.8]
    with SessionLocal() as session:
        _run(session, stock_code=stock_code, raw_scores=raw_scores)


def _run(session: Session, *, stock_code: str, raw_scores: list[float]) -> None:
    service = PatternScoreCalibrationService(session)
    print(f"stock_code={stock_code}")
    for raw in raw_scores:
        cal_5d = service.predict(stock_code=stock_code, raw_score=raw, horizon_days=5, method="platt")
        cal_10d = service.predict(stock_code=stock_code, raw_score=raw, horizon_days=10, method="platt")
        print(f"raw={raw:.2f}  cal_5d={cal_5d:.4f}  cal_10d={cal_10d:.4f}")


if __name__ == "__main__":
    main()
