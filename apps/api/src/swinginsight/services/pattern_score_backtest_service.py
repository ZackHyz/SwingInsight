from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice
from swinginsight.db.models.pattern import PatternFeature, PatternWindow
from swinginsight.db.models.prediction import BacktestResult
from swinginsight.services.feature_catalog import ALL_FEATURE_NAMES, COARSE_FEATURE_NAMES, pattern_feature_to_dict


@dataclass(slots=True, frozen=True)
class _WindowFeature:
    window: PatternWindow
    feature: PatternFeature


class PatternScoreBacktestService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def run_backtest(
        self,
        *,
        stock_code: str,
        start: date,
        end: date,
        horizon_days: list[int],
        top_k: int = 10,
        min_reference_size: int = 10,
        min_similarity: float = 0.0,
        min_samples: int = 1,
        feature_names: list[str] | None = None,
    ) -> dict[str, int]:
        windows = self._load_windows_with_features(stock_code=stock_code)
        if not windows:
            return {"processed_queries": 0, "written_rows": 0}

        query_windows = [row for row in windows if row.window.start_date >= start and row.window.end_date <= end]
        if not query_windows:
            return {"processed_queries": 0, "written_rows": 0}

        query_ids = [row.window.id for row in query_windows]
        self.session.execute(
            delete(BacktestResult).where(
                BacktestResult.stock_code == stock_code,
                BacktestResult.window_id.in_(query_ids),
                BacktestResult.horizon_days.in_(horizon_days),
            )
        )

        price_rows = self.session.scalars(
            select(DailyPrice)
            .where(DailyPrice.stock_code == stock_code)
            .order_by(DailyPrice.trade_date.asc(), DailyPrice.id.asc())
        ).all()
        trade_dates = [row.trade_date for row in price_rows]
        close_prices = [float(row.close_price) for row in price_rows]
        index_by_date = {trade_date: index for index, trade_date in enumerate(trade_dates)}

        written_rows = 0
        feature_keys = self._resolve_feature_keys(feature_names)
        for query in query_windows:
            references = [
                row
                for row in windows
                if row.window.id != query.window.id and row.window.end_date < query.window.start_date
            ]
            if len(references) < min_reference_size:
                continue
            ranked = self._rank_references(
                query=query,
                references=references,
                top_k=top_k,
                min_similarity=min_similarity,
                feature_keys=feature_keys,
            )
            if len(ranked) < max(min_samples, 1):
                continue
            if not ranked:
                continue
            latest_ref_end = max(item.window.end_date for item, _ in ranked)
            for horizon in horizon_days:
                predicted_win_rate, predicted_avg_return = self._predicted_stats(ranked=ranked, horizon=horizon)
                actual_return = self._forward_return(
                    index_by_date=index_by_date,
                    close_prices=close_prices,
                    anchor_date=query.window.end_date,
                    horizon=horizon,
                )
                row = BacktestResult(
                    stock_code=stock_code,
                    window_id=query.window.id,
                    horizon_days=horizon,
                    query_start_date=query.window.start_date,
                    query_end_date=query.window.end_date,
                    ref_latest_end_date=latest_ref_end,
                    predicted_win_rate=predicted_win_rate,
                    predicted_avg_return=predicted_avg_return,
                    actual_return=actual_return,
                    actual_outcome=1 if actual_return is not None and actual_return > 0 else (0 if actual_return is not None else None),
                    sample_count=len(ranked),
                )
                self.session.add(row)
                written_rows += 1

        return {"processed_queries": len(query_windows), "written_rows": written_rows}

    def summarize(
        self,
        *,
        stock_code: str,
        horizon: int,
        min_sample_count: int = 5,
        processed_queries: int | None = None,
    ) -> dict[str, object]:
        rows = self.session.scalars(
            select(BacktestResult)
            .where(
                BacktestResult.stock_code == stock_code,
                BacktestResult.horizon_days == horizon,
                BacktestResult.sample_count >= min_sample_count,
                BacktestResult.actual_outcome.is_not(None),
            )
            .order_by(BacktestResult.id.asc())
        ).all()
        if not rows:
            return {
                "stock_code": stock_code,
                "horizon": horizon,
                "rows": 0,
                "brier_score": 0.0,
                "tiers": self._empty_tiers(),
                "coverage_rate": 0.0,
                "sample_count_distribution": {},
            }
        brier = sum((float(row.predicted_win_rate) - int(row.actual_outcome or 0)) ** 2 for row in rows) / len(rows)
        denominator = processed_queries if processed_queries and processed_queries > 0 else len(rows)
        return {
            "stock_code": stock_code,
            "horizon": horizon,
            "rows": len(rows),
            "brier_score": round(brier, 4),
            "tiers": self._tier_summary(rows),
            "coverage_rate": round(len(rows) / denominator, 4) if denominator > 0 else 0.0,
            "sample_count_distribution": self._sample_count_distribution(rows),
        }

    def _load_windows_with_features(self, *, stock_code: str) -> list[_WindowFeature]:
        windows = self.session.scalars(
            select(PatternWindow)
            .where(PatternWindow.stock_code == stock_code)
            .order_by(PatternWindow.start_date.asc(), PatternWindow.end_date.asc(), PatternWindow.id.asc())
        ).all()
        if not windows:
            return []
        window_ids = [window.id for window in windows]
        features = self.session.scalars(select(PatternFeature).where(PatternFeature.window_id.in_(window_ids))).all()
        feature_by_window = {feature.window_id: feature for feature in features}
        return [
            _WindowFeature(window=window, feature=feature_by_window[window.id])
            for window in windows
            if window.id in feature_by_window
        ]

    def _rank_references(
        self,
        *,
        query: _WindowFeature,
        references: list[_WindowFeature],
        top_k: int,
        min_similarity: float,
        feature_keys: list[str] | None,
    ) -> list[tuple[_WindowFeature, float]]:
        ranked: list[tuple[_WindowFeature, float]] = []
        query_vector = self._build_vector(query.feature, feature_keys=feature_keys)
        if query_vector is None:
            return []
        reference_vectors: list[list[float]] = []
        aligned_refs: list[_WindowFeature] = []
        for reference in references:
            vector = self._build_vector(reference.feature, feature_keys=feature_keys)
            if vector is None:
                continue
            reference_vectors.append(vector)
            aligned_refs.append(reference)
        normalized_query, normalized_references = self._zscore_normalize(query_vector=query_vector, reference_vectors=reference_vectors)
        for reference, reference_vector in zip(aligned_refs, normalized_references, strict=False):
            score = self._cosine_similarity(normalized_query, reference_vector)
            if score < min_similarity:
                continue
            ranked.append((reference, score))
        ranked.sort(key=lambda item: item[1], reverse=True)
        return ranked[:max(top_k, 1)]

    def _predicted_stats(self, *, ranked: list[tuple[_WindowFeature, float]], horizon: int) -> tuple[float, float]:
        weighted_win = 0.0
        weighted_ret = 0.0
        weight_sum = 0.0
        for item, score in ranked:
            weight = max(score, 0.0001)
            ref_return = self._forward_return_by_window(item.window, horizon=horizon)
            if ref_return is None:
                continue
            weighted_win += weight * (1.0 if ref_return > 0 else 0.0)
            weighted_ret += weight * ref_return
            weight_sum += weight
        if weight_sum == 0:
            return 0.0, 0.0
        return round(weighted_win / weight_sum, 4), round(weighted_ret / weight_sum, 4)

    def _forward_return_by_window(self, window: PatternWindow, *, horizon: int) -> float | None:
        rows = self.session.scalars(
            select(DailyPrice)
            .where(
                DailyPrice.stock_code == window.stock_code,
                DailyPrice.trade_date >= window.end_date,
            )
            .order_by(DailyPrice.trade_date.asc(), DailyPrice.id.asc())
            .limit(horizon + 1)
        ).all()
        if len(rows) <= horizon:
            return None
        anchor = float(rows[0].close_price or 0.0)
        if anchor <= 0:
            return None
        return round(float(rows[horizon].close_price) / anchor - 1.0, 4)

    def _forward_return(
        self,
        *,
        index_by_date: dict[date, int],
        close_prices: list[float],
        anchor_date: date,
        horizon: int,
    ) -> float | None:
        index = index_by_date.get(anchor_date)
        if index is None:
            return None
        target = index + horizon
        if target >= len(close_prices):
            return None
        anchor = close_prices[index]
        if anchor <= 0:
            return None
        return round(close_prices[target] / anchor - 1.0, 4)

    def _cosine_similarity(self, left: list[float], right: list[float]) -> float:
        size = min(len(left), len(right))
        if size == 0:
            return 0.0
        left = left[:size]
        right = right[:size]
        numerator = sum(lv * rv for lv, rv in zip(left, right, strict=False))
        left_norm = sum(lv * lv for lv in left) ** 0.5
        right_norm = sum(rv * rv for rv in right) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return 0.0
        return (numerator / (left_norm * right_norm) + 1.0) / 2.0

    def _empty_tiers(self) -> list[dict[str, object]]:
        return [
            {"tier": "low", "pred": 0.0, "actual": 0.0, "n": 0},
            {"tier": "mid", "pred": 0.0, "actual": 0.0, "n": 0},
            {"tier": "high", "pred": 0.0, "actual": 0.0, "n": 0},
        ]

    def _tier_summary(self, rows: list[BacktestResult]) -> list[dict[str, object]]:
        buckets = [
            ("low", 0.0, 0.4),
            ("mid", 0.4, 0.65),
            ("high", 0.65, 1.01),
        ]
        tier_rows: list[dict[str, object]] = []
        for label, left, right in buckets:
            matched = [row for row in rows if left <= float(row.predicted_win_rate) < right]
            if not matched:
                tier_rows.append({"tier": label, "pred": 0.0, "actual": 0.0, "n": 0})
                continue
            pred = sum(float(row.predicted_win_rate) for row in matched) / len(matched)
            actual = sum(int(row.actual_outcome or 0) for row in matched) / len(matched)
            tier_rows.append({"tier": label, "pred": round(pred, 4), "actual": round(actual, 4), "n": len(matched)})
        return tier_rows

    def _sample_count_distribution(self, rows: list[BacktestResult]) -> dict[str, int]:
        buckets = {"<5": 0, "5-9": 0, "10-19": 0, "20-29": 0, "30+": 0}
        for row in rows:
            count = int(row.sample_count)
            if count < 5:
                buckets["<5"] += 1
            elif count < 10:
                buckets["5-9"] += 1
            elif count < 20:
                buckets["10-19"] += 1
            elif count < 30:
                buckets["20-29"] += 1
            else:
                buckets["30+"] += 1
        return buckets

    def _resolve_feature_keys(self, feature_names: list[str] | None) -> list[str] | None:
        if feature_names is None or len(feature_names) == 0:
            return None
        keys: list[str] = []
        invalid: list[str] = []
        for name in feature_names:
            if name not in ALL_FEATURE_NAMES:
                invalid.append(name)
                continue
            keys.append(name)
        if invalid:
            raise ValueError(f"Unknown feature names: {invalid}")
        if not keys:
            return None
        return sorted(set(keys))

    def _build_vector(self, row: PatternFeature, *, feature_keys: list[str] | None) -> list[float] | None:
        payload = pattern_feature_to_dict(row)
        if feature_keys is None:
            if not all(name in payload for name in COARSE_FEATURE_NAMES):
                return None
            return [payload[name] for name in COARSE_FEATURE_NAMES]
        if not all(name in payload for name in feature_keys):
            return None
        return [payload[name] for name in feature_keys]

    def _zscore_normalize(
        self,
        *,
        query_vector: list[float],
        reference_vectors: list[list[float]],
    ) -> tuple[list[float], list[list[float]]]:
        if not reference_vectors:
            return query_vector, []
        size = min([len(query_vector), *[len(vector) for vector in reference_vectors]])
        if size == 0:
            return [], []
        all_vectors = [query_vector[:size], *[vector[:size] for vector in reference_vectors]]
        means = [sum(vector[idx] for vector in all_vectors) / len(all_vectors) for idx in range(size)]
        stds: list[float] = []
        for idx in range(size):
            variance = sum((vector[idx] - means[idx]) ** 2 for vector in all_vectors) / len(all_vectors)
            stds.append(variance ** 0.5)

        def normalize(vector: list[float]) -> list[float]:
            values: list[float] = []
            for idx in range(size):
                std = stds[idx]
                if std == 0:
                    values.append(0.0)
                    continue
                values.append((vector[idx] - means[idx]) / std)
            return values

        normalized_query = normalize(query_vector[:size])
        normalized_refs = [normalize(vector[:size]) for vector in reference_vectors]
        return normalized_query, normalized_refs
