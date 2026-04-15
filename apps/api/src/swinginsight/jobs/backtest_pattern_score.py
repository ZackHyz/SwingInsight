from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from swinginsight.db.session import session_scope
from swinginsight.services.pattern_score_backtest_service import PatternScoreBacktestService


@dataclass(slots=True, frozen=True)
class BacktestPatternScoreResult:
    processed_queries: int
    written_rows: int
    summaries: list[dict[str, object]]


def backtest_pattern_score(
    *,
    stock_code: str,
    start: date,
    end: date,
    horizon_days: list[int],
    top_k: int = 10,
    min_reference_size: int = 10,
    min_similarity: float = 0.70,
    min_samples: int = 5,
    feature_names: list[str] | None = None,
    min_sample_count: int = 5,
) -> BacktestPatternScoreResult:
    with session_scope() as session:
        service = PatternScoreBacktestService(session)
        result = service.run_backtest(
            stock_code=stock_code,
            start=start,
            end=end,
            horizon_days=horizon_days,
            top_k=top_k,
            min_reference_size=min_reference_size,
            min_similarity=min_similarity,
            min_samples=min_samples,
            feature_names=feature_names,
        )
        session.flush()
        summaries = [
            service.summarize(
                stock_code=stock_code,
                horizon=horizon,
                min_sample_count=min_sample_count,
                processed_queries=int(result["processed_queries"]),
            )
            for horizon in horizon_days
        ]
    return BacktestPatternScoreResult(
        processed_queries=int(result["processed_queries"]),
        written_rows=int(result["written_rows"]),
        summaries=summaries,
    )
