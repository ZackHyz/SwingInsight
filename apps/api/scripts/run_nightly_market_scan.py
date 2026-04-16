from __future__ import annotations

from argparse import ArgumentParser
from datetime import datetime

from swinginsight.db.session import session_scope
from swinginsight.services.market_watchlist_service import MarketWatchlistService


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="Run nightly market scan and persist ranked watchlist rows.")
    parser.add_argument("--scan-date", default=None, help="Scan date in YYYY-MM-DD format, defaults to today.")
    parser.add_argument("--top-k", type=int, default=50, help="Maximum watchlist rows to persist.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    scan_date = datetime.strptime(args.scan_date, "%Y-%m-%d").date() if args.scan_date else None
    with session_scope() as session:
        summary = MarketWatchlistService(session).run_scan(scan_date=scan_date, top_k=args.top_k)
    print(f"scan_date={summary['scan_date']} rows={summary['rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
