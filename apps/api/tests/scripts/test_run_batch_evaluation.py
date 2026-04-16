from __future__ import annotations

from pathlib import Path
import sys

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def test_load_sample_pool_requires_four_categories(tmp_path) -> None:
    from scripts.run_batch_evaluation import load_sample_pool

    sample_pool = tmp_path / "sample_pool.json"
    sample_pool.write_text(
        """
{
  "version": "v1",
  "categories": {
    "trend_names": [],
    "range_names": []
  }
}
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError):
        load_sample_pool(sample_pool)


def test_run_batch_evaluation_writes_markdown_report(tmp_path, monkeypatch) -> None:
    from scripts.run_batch_evaluation import run_batch_evaluation

    sample_pool = tmp_path / "sample_pool.json"
    sample_pool.write_text(
        """
{
  "version": "v1",
  "categories": {
    "trend_names": [{"stock_code": "600001", "stock_name": "A"}],
    "range_names": [{"stock_code": "600002", "stock_name": "B"}],
    "announcement_heavy_names": [{"stock_code": "600003", "stock_name": "C"}],
    "low_liquidity_names": [{"stock_code": "600004", "stock_name": "D"}]
  }
}
""".strip(),
        encoding="utf-8",
    )
    report_path = tmp_path / "batch-eval.md"

    monkeypatch.setattr(
        "scripts.run_batch_evaluation._evaluate",
        lambda sample_pool, start, end, horizons: {
            "categories": {
                "trend_names": {"stocks": [], "summary": {"coverage_rate": 0.8, "brier_after": 0.2, "f1_exact": 0.7}},
                "range_names": {"stocks": [], "summary": {"coverage_rate": 0.6, "brier_after": 0.3, "f1_exact": 0.5}},
                "announcement_heavy_names": {"stocks": [], "summary": {"coverage_rate": 0.7, "brier_after": 0.25, "f1_exact": 0.6}},
                "low_liquidity_names": {"stocks": [], "summary": {"coverage_rate": 0.4, "brier_after": 0.4, "f1_exact": 0.3}},
            },
            "ranked_categories": [{"category": "trend_names", "score": 0.77, "reliability_rank": 1}],
            "failures": [],
            "total_success": 1,
        },
    )

    exit_code = run_batch_evaluation(
        sample_pool_path=sample_pool,
        start_date="2022-01-01",
        end_date="2025-12-31",
        horizons=[5, 10, 20],
        report_path=report_path,
    )

    assert exit_code == 0
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Batch Evaluation Report" in content
    assert "## Turning Point Evaluation" in content
    assert "trend_names" in content
