from __future__ import annotations

from pathlib import Path
import os
import sqlite3
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]


def run_cli(db_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    env["PYTHONPATH"] = str(ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "swinginsight.jobs.cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_news_pipeline_flow_backfills_processes_and_aligns(tmp_path) -> None:
    db_path = tmp_path / "news-pipeline.db"

    daily_prices = run_cli(db_path, "import-daily-prices", "--stock-code", "000001", "--demo")
    rebuild = run_cli(db_path, "rebuild-segments", "--stock-code", "000001", "--algo", "zigzag", "--demo")
    news_import = run_cli(db_path, "import-news", "--stock-code", "000001", "--demo")
    process = run_cli(db_path, "process-news", "--stock-code", "000001")
    align = run_cli(db_path, "align-news", "--stock-code", "000001")

    assert daily_prices.returncode == 0
    assert rebuild.returncode == 0
    assert news_import.returncode == 0
    assert process.returncode == 0
    assert align.returncode == 0
    assert "sentiment_results=" in process.stdout
    assert "event_results=" in process.stdout
    assert "conflict_news=" in process.stdout

    connection = sqlite3.connect(db_path)
    try:
        processed_rows = connection.execute("select count(*) from news_processed").fetchone()
        point_rows = connection.execute("select count(*) from point_news_map").fetchone()
        segment_rows = connection.execute("select count(*) from segment_news_map").fetchone()
        task_types = {
            row[0]
            for row in connection.execute(
                "select task_type from task_run_log where task_type in ('import_news', 'process_news', 'align_news')"
            ).fetchall()
        }
        assert processed_rows[0] > 0
        assert point_rows[0] > 0
        assert segment_rows[0] > 0
        assert task_types == {"import_news", "process_news", "align_news"}
    finally:
        connection.close()
