from __future__ import annotations

from pathlib import Path
import os
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from swinginsight.db.base import Base
from swinginsight.db.session import get_engine, session_scope
from swinginsight.demo_seed import (
    DEFAULT_DEMO_DATABASE_URL,
    DEMO_PREDICT_DATE,
    DEMO_STOCK_CODE,
    seed_demo_research_data,
)


def main() -> int:
    os.environ.setdefault("DATABASE_URL", DEFAULT_DEMO_DATABASE_URL)
    Base.metadata.create_all(get_engine())
    with session_scope() as session:
        result = seed_demo_research_data(session)

    print(
        f"seeded-demo-data stock_code={DEMO_STOCK_CODE} "
        f"database_url={os.environ['DATABASE_URL']} "
        f"predict_date={DEMO_PREDICT_DATE.isoformat()} "
        f"segment_id={result['segment_id']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
