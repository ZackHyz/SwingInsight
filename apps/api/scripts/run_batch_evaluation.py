from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import argparse
import json
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swinginsight.db.session import session_scope
from swinginsight.services.batch_evaluation_service import BatchEvaluationService


REQUIRED_CATEGORIES = {
    "trend_names",
    "range_names",
    "announcement_heavy_names",
    "low_liquidity_names",
}


def load_sample_pool(path: Path) -> dict[str, list[dict[str, str]]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    categories = payload.get("categories")
    if not isinstance(categories, dict):
        raise ValueError("sample pool categories must be an object")

    keys = set(categories.keys())
    if keys != REQUIRED_CATEGORIES:
        raise ValueError(
            "sample pool categories mismatch: "
            f"expected={sorted(REQUIRED_CATEGORIES)} actual={sorted(keys)}"
        )

    normalized: dict[str, list[dict[str, str]]] = {}
    for category, rows in categories.items():
        if not isinstance(rows, list):
            raise ValueError(f"category {category} must be a list")
        normalized_rows: list[dict[str, str]] = []
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError(f"category {category} entries must be objects")
            stock_code = str(row.get("stock_code", "")).strip()
            stock_name = str(row.get("stock_name", "")).strip()
            if not stock_code or not stock_name:
                raise ValueError(f"category {category} entry missing stock_code/stock_name")
            normalized_rows.append(
                {
                    "stock_code": stock_code,
                    "stock_name": stock_name,
                    "note": str(row.get("note", "")).strip(),
                }
            )
        normalized[category] = normalized_rows
    return normalized


def run_batch_evaluation(
    *,
    sample_pool_path: Path,
    start_date: str,
    end_date: str,
    horizons: list[int],
    report_path: Path | None = None,
) -> int:
    sample_pool = load_sample_pool(sample_pool_path)
    start = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    evaluation = _evaluate(sample_pool=sample_pool, start=start, end=end, horizons=horizons)

    output_path = report_path or _default_report_path()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        _render_markdown(
            sample_pool_path=sample_pool_path,
            horizons=horizons,
            start=start,
            end=end,
            evaluation=evaluation,
        ),
        encoding="utf-8",
    )
    print(f"batch-evaluation report={output_path}")
    return 0 if int(evaluation.get("total_success", 0)) > 0 else 1


def _evaluate(
    *,
    sample_pool: dict[str, list[dict[str, str]]],
    start: date,
    end: date,
    horizons: list[int],
) -> dict[str, object]:
    with session_scope() as session:
        return BatchEvaluationService(session).evaluate_batch(
            sample_pool=sample_pool,
            start=start,
            end=end,
            horizons=horizons,
        )


def _default_report_path() -> Path:
    now = datetime.now()
    filename = now.strftime("batch-eval-%Y%m%d-%H%M.md")
    return Path(__file__).resolve().parents[1] / "reports" / "evaluation" / filename


def _render_markdown(
    *,
    sample_pool_path: Path,
    horizons: list[int],
    start: date,
    end: date,
    evaluation: dict[str, object],
) -> str:
    lines = [
        "# Batch Evaluation Report",
        "",
        f"- Sample pool: `{sample_pool_path}`",
        f"- Range: `{start.isoformat()}` to `{end.isoformat()}`",
        f"- Horizons: `{', '.join(str(h) for h in horizons)}`",
        f"- Total successful symbols: `{evaluation.get('total_success', 0)}`",
        "",
        "## Turning Point Evaluation",
        "",
        "| Category | Coverage | Brier(after) | F1(exact) |",
        "| --- | ---: | ---: | ---: |",
    ]
    categories = evaluation.get("categories", {})
    if isinstance(categories, dict):
        for category, payload in categories.items():
            summary = payload.get("summary", {}) if isinstance(payload, dict) else {}
            lines.append(
                f"| {category} | {float(summary.get('coverage_rate', 0.0)):.4f} | "
                f"{float(summary.get('brier_after', 0.0)):.4f} | {float(summary.get('f1_exact', 0.0)):.4f} |"
            )

    lines.extend(
        [
            "",
            "## Pattern Ranking Evaluation",
            "",
            "Pattern metrics are aggregated per category in the table above; stock-level details are retained in runtime payload.",
            "",
            "## Calibration Evaluation",
            "",
            "Calibration metrics are aggregated per category and ranked below.",
            "",
            "| Rank | Category | Score |",
            "| ---: | --- | ---: |",
        ]
    )
    ranked_categories = evaluation.get("ranked_categories", [])
    if isinstance(ranked_categories, list):
        for item in ranked_categories:
            if not isinstance(item, dict):
                continue
            lines.append(
                f"| {int(item.get('reliability_rank', 0))} | {item.get('category', '--')} | {float(item.get('score', 0.0)):.4f} |"
            )

    failures = evaluation.get("failures", [])
    lines.extend(["", "## Failures", ""])
    if isinstance(failures, list) and failures:
        for failure in failures:
            if not isinstance(failure, dict):
                continue
            lines.append(
                f"- `{failure.get('category', '--')}` / `{failure.get('stock_code', '--')}`: {failure.get('error', '--')}"
            )
    else:
        lines.append("- None")
    lines.append("")
    return "\n".join(lines)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_batch_evaluation")
    parser.add_argument(
        "--sample-pool",
        default=str(Path(__file__).resolve().parents[1] / "config" / "evaluation" / "sample_pool.v1.json"),
    )
    parser.add_argument("--start", default="2022-01-01")
    parser.add_argument("--end", default="2025-12-31")
    parser.add_argument("--horizons", nargs="+", type=int, default=[5, 10, 20])
    parser.add_argument("--report-path")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    report_path = Path(args.report_path) if args.report_path else None
    return run_batch_evaluation(
        sample_pool_path=Path(args.sample_pool),
        start_date=args.start,
        end_date=args.end,
        horizons=list(args.horizons),
        report_path=report_path,
    )


if __name__ == "__main__":
    raise SystemExit(main())
