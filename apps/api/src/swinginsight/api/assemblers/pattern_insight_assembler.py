from __future__ import annotations

from datetime import date

from swinginsight.services.pattern_score_calibration_service import PatternScoreCalibrationService


def build_pattern_score_snapshot(
    summary: dict[str, object],
    *,
    stock_code: str,
    calibration_service: PatternScoreCalibrationService,
    query_end_date: date | None,
) -> dict[str, object]:
    similar_cases = _resolve_similar_cases(summary)
    horizon = 10
    raw_win_rate_5d = _win_rate(similar_cases, horizon=5)
    raw_win_rate_10d = _win_rate(similar_cases, horizon=10)
    win_rate_5d, calibrated_5d = calibration_service.predict_with_meta(
        stock_code=stock_code,
        raw_score=raw_win_rate_5d,
        horizon_days=5,
        method="platt",
    )
    win_rate_10d, calibrated_10d = calibration_service.predict_with_meta(
        stock_code=stock_code,
        raw_score=raw_win_rate_10d,
        horizon_days=10,
        method="platt",
    )
    weighted = _weighted_return(similar_cases, horizon=horizon)
    sample_count = int(weighted["sample_count"])
    payload = {
        "horizon_days": horizon,
        "raw_win_rate": raw_win_rate_10d,
        "win_rate_5d": round(win_rate_5d, 4),
        "win_rate_10d": round(win_rate_10d, 4),
        "win_rate": round(win_rate_10d, 4),
        "avg_return": weighted["avg_return"],
        "sample_count": sample_count,
        "confidence": _resolve_confidence(sample_count),
        "calibrated": bool(calibrated_5d and calibrated_10d),
    }
    query_window = summary.get("query_window") if isinstance(summary, dict) else None
    query_window_id = query_window.get("window_id") if isinstance(query_window, dict) else None
    return {
        "payload": payload,
        "query_window_id": query_window_id if isinstance(query_window_id, int) else None,
        "query_end_date": query_end_date or resolve_query_end_date(summary),
    }


def build_pattern_similar_cases_payload(
    summary: dict[str, object],
    *,
    top_k: int = 10,
) -> list[dict[str, object]]:
    items = _resolve_similar_cases(summary)[: max(top_k, 0)]
    return [
        {
            "window_id": item.get("window_id"),
            "window_start_date": item.get("window_start_date"),
            "window_end_date": item.get("window_end_date"),
            "segment_start_date": item.get("segment_start_date") or item.get("start_date"),
            "segment_end_date": item.get("segment_end_date") or item.get("end_date"),
            "similarity_score": float(item.get("score") or 0.0),
            "future_return_5d": item.get("return_5d"),
            "future_return_10d": item.get("return_10d"),
            "future_return_20d": item.get("return_20d"),
            "stock_code": item.get("stock_code"),
            "segment_id": item.get("segment_id"),
        }
        for item in items
    ]


def build_pattern_group_stat_payload(summary: dict[str, object]) -> dict[str, object]:
    similar_cases = _resolve_similar_cases(summary)
    horizons = (5, 10, 20)
    return_distributions = {
        str(horizon): _return_distribution(similar_cases, horizon=horizon) for horizon in horizons
    }
    return {
        "horizon_days": list(horizons),
        "win_rates": [_win_rate(similar_cases, horizon=horizon) for horizon in horizons],
        "avg_returns": [_weighted_return(similar_cases, horizon=horizon)["avg_return"] for horizon in horizons],
        "sample_counts": [_sample_count(similar_cases, horizon=horizon) for horizon in horizons],
        "return_distribution": return_distributions["10"],
        "return_distributions": return_distributions,
    }


def resolve_query_end_date(summary: dict[str, object]) -> date | None:
    query_window = summary.get("query_window") if isinstance(summary, dict) else None
    end_value = query_window.get("end_date") if isinstance(query_window, dict) else None
    return _as_iso_date(end_value)


def _resolve_similar_cases(summary: dict[str, object]) -> list[dict[str, object]]:
    items = summary.get("similar_cases")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, dict)]


def _safe_float(value: object) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_iso_date(value: object) -> date | None:
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            return None
    return None


def _weighted_return(similar_cases: list[dict[str, object]], *, horizon: int) -> dict[str, float | int]:
    weighted_sum = 0.0
    weight_total = 0.0
    sample_count = 0
    for item in similar_cases:
        future_return = _safe_float(item.get(f"return_{horizon}d"))
        if future_return is None:
            continue
        weight = _safe_float(item.get("score")) or 0.0
        if weight <= 0:
            weight = 0.0001
        weighted_sum += weight * future_return
        weight_total += weight
        sample_count += 1
    if sample_count == 0:
        return {"avg_return": 0.0, "sample_count": 0}
    avg_return = weighted_sum / weight_total if weight_total > 0 else 0.0
    return {"avg_return": round(avg_return, 4), "sample_count": sample_count}


def _sample_count(similar_cases: list[dict[str, object]], *, horizon: int) -> int:
    return sum(1 for item in similar_cases if _safe_float(item.get(f"return_{horizon}d")) is not None)


def _win_rate(similar_cases: list[dict[str, object]], *, horizon: int) -> float:
    values = [
        value
        for value in (_safe_float(item.get(f"return_{horizon}d")) for item in similar_cases)
        if value is not None
    ]
    if not values:
        return 0.0
    return round(sum(1 for value in values if value > 0) / len(values), 4)


def _resolve_confidence(sample_count: int) -> str:
    if sample_count >= 30:
        return "high"
    if sample_count >= 10:
        return "medium"
    return "low"


def _return_distribution(similar_cases: list[dict[str, object]], *, horizon: int) -> list[float]:
    values = [
        value
        for value in (_safe_float(item.get(f"return_{horizon}d")) for item in similar_cases)
        if value is not None
    ]
    return sorted(round(value, 4) for value in values)
