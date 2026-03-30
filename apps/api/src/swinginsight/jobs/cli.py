from __future__ import annotations

import argparse
from datetime import date

from swinginsight.jobs.import_market_data import import_daily_prices
from swinginsight.jobs.materialize_features import materialize_features
from swinginsight.jobs.rebuild_segments import rebuild_segments


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="swinginsight")
    subparsers = parser.add_subparsers(dest="command", required=True)

    daily_prices = subparsers.add_parser("import-daily-prices")
    daily_prices.add_argument("--stock-code", required=True)
    daily_prices.add_argument("--start")
    daily_prices.add_argument("--end")
    daily_prices.add_argument("--demo", action="store_true")

    segment_rebuild = subparsers.add_parser("rebuild-segments")
    segment_rebuild.add_argument("--stock-code", required=True)
    segment_rebuild.add_argument("--algo", default="zigzag")
    segment_rebuild.add_argument("--demo", action="store_true")

    materialize = subparsers.add_parser("materialize-features")
    materialize.add_argument("--stock-code", required=True)
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

    if args.command == "rebuild-segments":
        result = rebuild_segments(stock_code=args.stock_code, algo=args.algo, demo=args.demo)
        print(
            f"rebuild-segments stock_code={args.stock_code} algo={args.algo} "
            f"turning_points={result.turning_points} segments={result.segments} version={result.version_code}"
        )
        return 0

    if args.command == "materialize-features":
        result = materialize_features(stock_code=args.stock_code)
        print(
            f"materialize-features stock_code={args.stock_code} "
            f"segments={result.segments} features={result.features}"
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
