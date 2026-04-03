from __future__ import annotations

import argparse
from datetime import date

from swinginsight.jobs.align_news import align_news
from swinginsight.jobs.build_pattern_windows import build_pattern_windows
from swinginsight.jobs.import_market_data import import_daily_prices
from swinginsight.jobs.import_news import import_news
from swinginsight.jobs.materialize_features import materialize_features
from swinginsight.jobs.materialize_pattern_features import materialize_pattern_features
from swinginsight.jobs.materialize_pattern_future_stats import materialize_pattern_future_stats
from swinginsight.jobs.predict_state import predict_state
from swinginsight.jobs.process_news import process_news
from swinginsight.jobs.rebuild_segments import rebuild_segments


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="swinginsight",
        epilog=(
            "单股 pattern 回填顺序:\n"
            "  rebuild-segments -> build-pattern-windows -> materialize-pattern-features -> materialize-pattern-future-stats"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    daily_prices = subparsers.add_parser("import-daily-prices")
    daily_prices.add_argument("--stock-code", required=True)
    daily_prices.add_argument("--start")
    daily_prices.add_argument("--end")
    daily_prices.add_argument("--demo", action="store_true")

    news_import = subparsers.add_parser("import-news")
    news_import.add_argument("--stock-code", required=True)
    news_import.add_argument("--start")
    news_import.add_argument("--end")
    news_import.add_argument("--source", action="append", dest="sources")
    news_import.add_argument("--demo", action="store_true")

    process_news_parser = subparsers.add_parser("process-news")
    process_news_parser.add_argument("--stock-code", required=True)
    process_news_parser.add_argument("--start")
    process_news_parser.add_argument("--end")

    align_news_parser = subparsers.add_parser("align-news")
    align_news_parser.add_argument("--stock-code", required=True)
    align_news_parser.add_argument("--start")
    align_news_parser.add_argument("--end")

    segment_rebuild = subparsers.add_parser("rebuild-segments")
    segment_rebuild.add_argument("--stock-code", required=True)
    segment_rebuild.add_argument("--algo", default="zigzag")
    segment_rebuild.add_argument("--demo", action="store_true")

    materialize = subparsers.add_parser("materialize-features")
    materialize.add_argument("--stock-code", required=True)

    pattern_windows = subparsers.add_parser(
        "build-pattern-windows",
        help="为单只股票生成固定 7 日滑窗检索样本",
    )
    pattern_windows.add_argument("--stock-code", required=True)
    pattern_windows.add_argument("--window-size", type=int, default=7)

    pattern_future = subparsers.add_parser(
        "materialize-pattern-future-stats",
        help="为滑窗样本预计算后续 1/3/5/10 日收益统计",
    )
    pattern_future.add_argument("--stock-code", required=True)

    pattern_features = subparsers.add_parser(
        "materialize-pattern-features",
        help="为滑窗样本生成粗召回和精排特征",
    )
    pattern_features.add_argument("--stock-code", required=True)

    predict = subparsers.add_parser("predict-state")
    predict.add_argument("--stock-code", required=True)
    predict.add_argument("--predict-date", required=True)
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

    if args.command == "import-news":
        inserted = import_news(
            stock_code=args.stock_code,
            start=parse_optional_date(args.start),
            end=parse_optional_date(args.end),
            demo=args.demo,
            source_list=args.sources,
        )
        print(f"import-news stock_code={args.stock_code} inserted={inserted}")
        return 0

    if args.command == "process-news":
        result = process_news(
            stock_code=args.stock_code,
            start=parse_optional_date(args.start),
            end=parse_optional_date(args.end),
        )
        print(
            f"process-news stock_code={args.stock_code} "
            f"processed={result.processed_count} duplicates={result.duplicates} "
            f"sentiment_results={result.sentiment_results} event_results={result.event_results} "
            f"conflict_news={result.conflict_news}"
        )
        return 0

    if args.command == "align-news":
        result = align_news(
            stock_code=args.stock_code,
            start=parse_optional_date(args.start),
            end=parse_optional_date(args.end),
        )
        print(
            f"align-news stock_code={args.stock_code} "
            f"point_mappings={result.point_mappings} segment_mappings={result.segment_mappings}"
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

    if args.command == "build-pattern-windows":
        result = build_pattern_windows(stock_code=args.stock_code, window_size=args.window_size)
        print(
            f"build-pattern-windows stock_code={args.stock_code} window_size={args.window_size} "
            f"created={result.created} updated={result.updated} skipped={result.skipped}"
        )
        return 0

    if args.command == "materialize-pattern-future-stats":
        result = materialize_pattern_future_stats(stock_code=args.stock_code)
        print(
            f"materialize-pattern-future-stats stock_code={args.stock_code} "
            f"updated={result.updated} skipped={result.skipped}"
        )
        return 0

    if args.command == "materialize-pattern-features":
        result = materialize_pattern_features(stock_code=args.stock_code)
        print(
            f"materialize-pattern-features stock_code={args.stock_code} "
            f"windows={result.windows} features={result.features} skipped={result.skipped}"
        )
        return 0

    if args.command == "predict-state":
        result = predict_state(stock_code=args.stock_code, predict_date=parse_optional_date(args.predict_date))
        print(
            f"predict-state stock_code={args.stock_code} predict_date={args.predict_date} "
            f"current_state={result.current_state} up_prob_10d={result.up_prob_10d:.4f}"
        )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
