from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import DailyPrice, TaskRunLog
from swinginsight.ingest.ports import DailyPriceFeed


@dataclass(slots=True)
class ImportResult:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0


class DailyPriceImporter:
    def __init__(self, session: Session, feed: DailyPriceFeed, source_name: str | None = None) -> None:
        self.session = session
        self.feed = feed
        self.source_name = source_name or feed.__class__.__name__

    def run(self, stock_code: str, start: date | None = None, end: date | None = None) -> ImportResult:
        started_at = datetime.now(UTC)
        payloads = self.feed.fetch_daily_prices(stock_code=stock_code, start=start, end=end)
        resolved_source_name = self._resolve_source_name(payloads)
        result = ImportResult()

        for payload in payloads:
            normalized_payload = self._normalize_payload(payload, resolved_source_name)
            existing = self.session.scalar(
                select(DailyPrice).where(
                    DailyPrice.stock_code == normalized_payload["stock_code"],
                    DailyPrice.trade_date == normalized_payload["trade_date"],
                    DailyPrice.adj_type == normalized_payload.get("adj_type", "qfq"),
                )
            )
            if existing is None:
                model = DailyPrice(**normalized_payload)
                self.session.add(model)
                result.inserted += 1
                continue

            changed = False
            for field, value in normalized_payload.items():
                if getattr(existing, field) != value:
                    setattr(existing, field, value)
                    changed = True
            if changed:
                result.updated += 1
            else:
                result.skipped += 1

        finished_at = datetime.now(UTC)
        self.session.add(
            TaskRunLog(
                task_name=f"import-daily-prices:{stock_code}",
                task_type="import_daily_price",
                target_code=stock_code,
                status="success",
                start_time=started_at,
                end_time=finished_at,
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                input_params_json={
                    "stock_code": stock_code,
                    "start": start.isoformat() if start else None,
                    "end": end.isoformat() if end else None,
                    "source": resolved_source_name,
                },
                result_summary=f"inserted={result.inserted},updated={result.updated},skipped={result.skipped}",
            )
        )
        self.session.commit()
        return result

    def _resolve_source_name(self, payloads: list[dict[str, Any]]) -> str:
        resolved_source_name = getattr(self.feed, "resolved_source_name", None)
        if resolved_source_name:
            return str(resolved_source_name)
        if payloads:
            first_data_source = payloads[0].get("data_source")
            if first_data_source:
                return str(first_data_source)
        return self.source_name

    def _normalize_payload(self, payload: dict[str, Any], resolved_source_name: str) -> dict[str, Any]:
        return {
            "stock_code": payload["stock_code"],
            "trade_date": payload["trade_date"],
            "open_price": payload["open_price"],
            "high_price": payload["high_price"],
            "low_price": payload["low_price"],
            "close_price": payload["close_price"],
            "pre_close_price": payload.get("pre_close_price"),
            "change_amount": payload.get("change_amount"),
            "change_pct": payload.get("change_pct"),
            "volume": payload.get("volume"),
            "amount": payload.get("amount"),
            "amplitude_pct": payload.get("amplitude_pct"),
            "turnover_rate": payload.get("turnover_rate"),
            "adj_type": payload.get("adj_type", "qfq"),
            "adj_factor": payload.get("adj_factor"),
            "is_trading_day": payload.get("is_trading_day", True),
            "data_source": payload.get("data_source") or resolved_source_name,
        }
