from __future__ import annotations

from dataclasses import dataclass

from swinginsight.db.session import session_scope
from swinginsight.services.score_validation_service import ScoreValidationService


@dataclass(slots=True, frozen=True)
class ScoreLogBackfillResult:
    updated: int


def backfill_score_log(*, stock_code: str | None = None) -> ScoreLogBackfillResult:
    with session_scope() as session:
        updated = ScoreValidationService(session).backfill_actual_returns(stock_code=stock_code)
    return ScoreLogBackfillResult(updated=updated)
