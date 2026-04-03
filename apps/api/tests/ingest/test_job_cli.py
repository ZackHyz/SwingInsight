from __future__ import annotations

from pathlib import Path
import sqlite3
import subprocess
import sys
import os


ROOT = Path(__file__).resolve().parents[2]


def test_cli_exposes_import_daily_prices(tmp_path) -> None:
    db_path = tmp_path / "cli-demo.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "swinginsight.jobs.cli",
            "import-daily-prices",
            "--stock-code",
            "000001",
            "--demo",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "inserted=2" in result.stdout

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("select count(*) from daily_price").fetchone()
        assert rows[0] == 2
    finally:
        connection.close()


def test_cli_rebuild_segments_persists_turning_points_and_segments(tmp_path) -> None:
    db_path = tmp_path / "cli-rebuild.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "swinginsight.jobs.cli",
            "rebuild-segments",
            "--stock-code",
            "000001",
            "--algo",
            "zigzag",
            "--demo",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "turning_points=3" in result.stdout
    assert "segments=2" in result.stdout

    connection = sqlite3.connect(db_path)
    try:
        turning_points = connection.execute("select count(*) from turning_point").fetchone()
        segments = connection.execute("select count(*) from swing_segment").fetchone()
        assert turning_points[0] == 3
        assert segments[0] == 2
    finally:
        connection.close()


def test_cli_exposes_import_news(tmp_path) -> None:
    db_path = tmp_path / "cli-news.db"
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+pysqlite:///{db_path}"
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "swinginsight.jobs.cli",
            "import-news",
            "--stock-code",
            "000001",
            "--start",
            "2024-01-01",
            "--end",
            "2024-01-31",
            "--demo",
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "import-news stock_code=000001 inserted=2" in result.stdout

    connection = sqlite3.connect(db_path)
    try:
        rows = connection.execute("select count(*) from news_raw").fetchone()
        assert rows[0] == 2
    finally:
        connection.close()


def test_cli_help_includes_pattern_backfill_order() -> None:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")

    result = subprocess.run(
        [sys.executable, "-m", "swinginsight.jobs.cli", "--help"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "build-pattern-windows -> materialize-pattern-features -> materialize-pattern-future-stats" in result.stdout
