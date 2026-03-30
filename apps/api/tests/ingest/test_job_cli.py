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
    assert "turning_points=4" in result.stdout
    assert "segments=3" in result.stdout

    connection = sqlite3.connect(db_path)
    try:
        turning_points = connection.execute("select count(*) from turning_point").fetchone()
        segments = connection.execute("select count(*) from swing_segment").fetchone()
        assert turning_points[0] == 4
        assert segments[0] == 3
    finally:
        connection.close()
