from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from swinginsight.db.models.market_data import TaskRunLog, TradeRecord
from swinginsight.ingest.ports import TradeRecordFeed


class TradeRecordImporter:
    def __init__(self, session: Session, feed: TradeRecordFeed, source_name: str | None = None) -> None:
        self.session = session
        self.feed = feed
        self.source_name = source_name or feed.__class__.__name__

    def run(self, stock_code: str, start: date | None = None, end: date | None = None) -> int:
        started_at = datetime.now(UTC)
        rows = self.feed.fetch_trade_records(stock_code=stock_code, start=start, end=end)
        for row in rows:
            self.session.add(TradeRecord(**row))
        finished_at = datetime.now(UTC)
        self.session.add(
            TaskRunLog(
                task_name=f"import-trade-records:{stock_code}",
                task_type="import_trade_record",
                target_code=stock_code,
                status="success",
                start_time=started_at,
                end_time=finished_at,
                duration_ms=int((finished_at - started_at).total_seconds() * 1000),
                input_params_json={"stock_code": stock_code, "source": self.source_name},
                result_summary=f"inserted={len(rows)}",
            )
        )
        self.session.commit()
        return len(rows)
