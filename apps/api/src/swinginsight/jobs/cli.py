from __future__ import annotations

import argparse
from datetime import date

from swinginsight.jobs.import_market_data import import_daily_prices


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swinginsight")
    subparsers = parser.add_subparsers(dest="command", required=True)

    daily_prices = subparsers.add_parser("import-daily-prices")
    daily_prices.add_argument("--stock-code", required=True)
    daily_prices.add_argument("--start")
    daily_prices.add_argument("--end")
    daily_prices.add_argument("--demo", action="store_true")
    return parser


def parse_optional_date(value: str | None) -> date | None:
    if not value:
        return None
    return date.fromisoformat(value)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "import-daily-prices":
        result = import_daily_prices(
            stock_code=args.stock_code,
            start=parse_optional_date(args.start),
            end=parse_optional_date(args.end),
            demo=args.demo,
        )
        print(
            f"import-daily-prices stock_code={args.stock_code} "
            f"inserted={result.inserted} updated={result.updated} skipped={result.skipped}"
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
