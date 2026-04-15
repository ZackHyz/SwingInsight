from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from swinginsight.jobs.diagnose_feature_signal import diagnose_feature_signal  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Diagnose coarse feature signal strength against backtest outcomes.")
    parser.add_argument("--stock-code", required=True)
    parser.add_argument("--horizon-days", type=int, default=5)
    parser.add_argument("--min-sample-count", type=int, default=5)
    parser.add_argument("--feature-names", nargs="+")
    parser.add_argument("--top-n", type=int, default=12)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    result = diagnose_feature_signal(
        stock_code=args.stock_code,
        horizon_days=args.horizon_days,
        min_sample_count=args.min_sample_count,
        feature_names=args.feature_names,
    )
    print(
        f"diagnose_feature_signal stock_code={result.stock_code} "
        f"horizon_days={result.horizon_days} strong_signal_count={result.strong_signal_count}"
    )
    if result.strong_features:
        print(f"strong_features={result.strong_features}")
    for row in result.rows[: max(args.top_n, 1)]:
        print(
            f"{row.feature:>12} r_outcome={row.r_outcome:+.4f} "
            f"r_return={row.r_return:+.4f} p_outcome={row.p_outcome:.4f} n={row.n}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
