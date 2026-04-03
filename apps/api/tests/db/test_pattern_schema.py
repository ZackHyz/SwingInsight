from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_pattern_tables_exist() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.pattern import PatternFeature, PatternFutureStat, PatternMatchResult, PatternWindow

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    inspector = inspect(engine)

    assert PatternWindow.__tablename__ in inspector.get_table_names()
    assert PatternFeature.__tablename__ in inspector.get_table_names()
    assert PatternFutureStat.__tablename__ in inspector.get_table_names()
    assert PatternMatchResult.__tablename__ in inspector.get_table_names()


def test_pattern_window_allows_multiple_windows_per_segment() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.pattern import PatternWindow
    from swinginsight.db.models.segment import SwingSegment

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)

    with Session() as session:
        segment = SwingSegment(
            segment_uid="seg-pattern-schema-1",
            stock_code="000001",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            start_point_type="trough",
            end_point_type="peak",
            start_price=10.0,
            end_price=12.0,
            pct_change=20.0,
            duration_days=14,
            segment_type="up_swing",
            trend_direction="up",
            source_version="test",
            is_final=True,
        )
        session.add(segment)
        session.flush()

        session.add(
            PatternWindow(
                window_uid="pw-000001-20240101-20240109",
                stock_code="000001",
                segment_id=segment.id,
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 9),
                window_size=7,
                start_close=10.0,
                end_close=10.8,
                period_pct_change=8.0,
                highest_day_pos=6,
                lowest_day_pos=0,
                trend_label="uptrend",
                feature_version="pattern:v1",
            )
        )
        session.add(
            PatternWindow(
                window_uid="pw-000001-20240102-20240110",
                stock_code="000001",
                segment_id=segment.id,
                start_date=date(2024, 1, 2),
                end_date=date(2024, 1, 10),
                window_size=7,
                start_close=10.2,
                end_close=11.0,
                period_pct_change=7.8,
                highest_day_pos=6,
                lowest_day_pos=0,
                trend_label="uptrend",
                feature_version="pattern:v1",
            )
        )
        session.commit()

        count = session.scalar(
            select(func.count()).select_from(PatternWindow).where(PatternWindow.segment_id == segment.id)
        )
        assert count == 2
