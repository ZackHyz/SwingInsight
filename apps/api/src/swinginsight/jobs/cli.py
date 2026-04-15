from __future__ import annotations

import argparse
from datetime import date

from swinginsight.jobs.align_news import align_news
from swinginsight.jobs.backfill_score_log import backfill_score_log
from swinginsight.jobs.backtest_pattern_score import backtest_pattern_score
from swinginsight.jobs.build_pattern_windows import build_pattern_windows
from swinginsight.jobs.calibrate_pattern_score import calibrate_pattern_score, verify_calibration
from swinginsight.jobs.diagnose_feature_signal import diagnose_feature_signal
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
    pattern_features.add_argument(
        "--feature-set",
        action="append",
        choices=["coarse", "volume_context", "price_position", "trend_context"],
    )

    predict = subparsers.add_parser("predict-state")
    predict.add_argument("--stock-code", required=True)
    predict.add_argument("--predict-date", required=True)

    score_backfill = subparsers.add_parser(
        "backfill-score-log",
        help="回填 score_log 的实际 5/10 日收益与涨跌结果",
    )
    score_backfill.add_argument("--stock-code")

    pattern_backtest = subparsers.add_parser(
        "backtest-pattern-score",
        help="按时序隔离规则回测历史 pattern score 预测质量",
    )
    pattern_backtest.add_argument("--stock-code", required=True)
    pattern_backtest.add_argument("--start", required=True)
    pattern_backtest.add_argument("--end", required=True)
    pattern_backtest.add_argument("--horizon-days", nargs="+", required=True, type=int)
    pattern_backtest.add_argument("--top-k", type=int, default=10)
    pattern_backtest.add_argument("--min-reference-size", type=int, default=10)
    pattern_backtest.add_argument("--min-similarity", type=float, default=0.70)
    pattern_backtest.add_argument("--min-samples", type=int, default=5)
    pattern_backtest.add_argument("--feature-names", nargs="+")
    pattern_backtest.add_argument("--min-sample-count", type=int, default=5)

    signal_diagnose = subparsers.add_parser(
        "diagnose-feature-signal",
        help="诊断 coarse 特征各维度与未来涨跌的相关性",
    )
    signal_diagnose.add_argument("--stock-code", required=True)
    signal_diagnose.add_argument("--horizon-days", type=int, default=5)
    signal_diagnose.add_argument("--min-sample-count", type=int, default=5)
    signal_diagnose.add_argument("--feature-names", nargs="+")

    calibrate_parser = subparsers.add_parser(
        "calibrate-pattern-score",
        help="基于 backtest_result 训练概率校准模型（isotonic/platt）",
    )
    calibrate_parser.add_argument("--stock-code", required=True)
    calibrate_parser.add_argument("--horizon-days", nargs="+", type=int, default=[5, 10])
    calibrate_parser.add_argument("--method", choices=["isotonic", "platt"], default="isotonic")
    calibrate_parser.add_argument("--train-ratio", type=float, default=0.7)
    calibrate_parser.add_argument("--min-sample-count", type=int, default=5)

    verify_parser = subparsers.add_parser(
        "verify-calibration",
        help="输出校准后的验证集曲线与单调性报告",
    )
    verify_parser.add_argument("--stock-code", required=True)
    verify_parser.add_argument("--horizon-days", type=int, default=10)
    verify_parser.add_argument("--method", choices=["isotonic", "platt"], default="isotonic")
    verify_parser.add_argument("--train-ratio", type=float, default=0.7)
    verify_parser.add_argument("--min-sample-count", type=int, default=5)
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
        feature_sets = args.feature_set if args.feature_set else ["coarse"]
        result = materialize_pattern_features(stock_code=args.stock_code, feature_sets=feature_sets)
        print(
            f"materialize-pattern-features stock_code={args.stock_code} "
            f"feature_sets={feature_sets} windows={result.windows} features={result.features} skipped={result.skipped}"
        )
        return 0

    if args.command == "predict-state":
        result = predict_state(stock_code=args.stock_code, predict_date=parse_optional_date(args.predict_date))
        print(
            f"predict-state stock_code={args.stock_code} predict_date={args.predict_date} "
            f"current_state={result.current_state} up_prob_10d={result.up_prob_10d:.4f}"
        )
        return 0

    if args.command == "backfill-score-log":
        result = backfill_score_log(stock_code=args.stock_code)
        scope = args.stock_code if args.stock_code else "ALL"
        print(f"backfill-score-log stock_code={scope} updated={result.updated}")
        return 0

    if args.command == "backtest-pattern-score":
        result = backtest_pattern_score(
            stock_code=args.stock_code,
            start=parse_optional_date(args.start),
            end=parse_optional_date(args.end),
            horizon_days=list(args.horizon_days),
            top_k=args.top_k,
            min_reference_size=args.min_reference_size,
            min_similarity=args.min_similarity,
            min_samples=args.min_samples,
            feature_names=args.feature_names,
            min_sample_count=args.min_sample_count,
        )
        print(
            f"backtest-pattern-score stock_code={args.stock_code} "
            f"processed_queries={result.processed_queries} written_rows={result.written_rows} "
            f"min_similarity={args.min_similarity:.2f} min_samples={args.min_samples} "
            f"feature_names={args.feature_names or 'ALL'}"
        )
        for summary in result.summaries:
            print(
                "  horizon={horizon} rows={rows} coverage={coverage} brier={brier} "
                "sample_count_dist={sample_count_dist} tiers={tiers}".format(
                    horizon=summary["horizon"],
                    rows=summary["rows"],
                    coverage=summary["coverage_rate"],
                    brier=summary["brier_score"],
                    sample_count_dist=summary["sample_count_distribution"],
                    tiers=summary["tiers"],
                )
            )
        return 0

    if args.command == "diagnose-feature-signal":
        result = diagnose_feature_signal(
            stock_code=args.stock_code,
            horizon_days=args.horizon_days,
            min_sample_count=args.min_sample_count,
            feature_names=args.feature_names,
        )
        print(
            f"diagnose-feature-signal stock_code={result.stock_code} "
            f"horizon_days={result.horizon_days} strong_signal_count={result.strong_signal_count}"
        )
        if result.strong_features:
            print(f"  strong_features={result.strong_features}")
        print("  top_rows:")
        for row in result.rows[:12]:
            print(
                f"    {row.feature:>12} r_outcome={row.r_outcome:+.4f} "
                f"r_return={row.r_return:+.4f} p_outcome={row.p_outcome:.4f} n={row.n}"
            )
        return 0

    if args.command == "calibrate-pattern-score":
        result = calibrate_pattern_score(
            stock_code=args.stock_code,
            horizon_days=list(args.horizon_days),
            method=args.method,
            train_ratio=args.train_ratio,
            min_sample_count=args.min_sample_count,
        )
        for report in result.reports:
            print(
                f"calibrate-pattern-score stock_code={report['stock_code']} "
                f"horizon={report['horizon_days']}d method={report['method']} "
                f"train_size={report['train_size']} val_size={report['val_size']} "
                f"brier_before={report['brier_before']:.4f} brier_after={report['brier_after']:.4f}"
            )
            for bucket in report["bucket_metrics"]:
                print(
                    "  bucket={bucket} n={n} error_before={error_before:.4f} "
                    "-> error_after={error_after:.4f}".format(
                        bucket=bucket.bucket,
                        n=bucket.n,
                        error_before=bucket.error_before,
                        error_after=bucket.error_after,
                    )
                )
            print(f"  model_path={report['model_path']}")
        return 0

    if args.command == "verify-calibration":
        report = verify_calibration(
            stock_code=args.stock_code,
            horizon_days=args.horizon_days,
            method=args.method,
            train_ratio=args.train_ratio,
            min_sample_count=args.min_sample_count,
        )
        print(
            f"verify-calibration stock_code={report['stock_code']} "
            f"horizon={report['horizon_days']}d method={report['method']} "
            f"val_size={report['val_size']} monotonic={report['is_monotonic']} "
            f"brier_before={report['brier_before']:.4f} brier_after={report['brier_after']:.4f}"
        )
        for row in report["curve_rows"]:
            print(
                "  bucket={bucket} n={n} raw_mean={raw_mean:.4f} "
                "cal_mean={cal_mean:.4f} actual_mean={actual_mean:.4f}".format(**row)
            )
        return 0

    parser.error(f"Unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
