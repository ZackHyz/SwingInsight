from datetime import date
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_segment_uid_is_unique() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.segment import SwingSegment

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)

    payload = dict(
        segment_uid="seg-0001",
        stock_code="000001",
        start_date=date(2024, 1, 2),
        end_date=date(2024, 1, 10),
        start_point_type="trough",
        end_point_type="peak",
        start_price=10,
        end_price=12,
    )

    with Session() as session:
        session.add(SwingSegment(**payload))
        session.commit()

        session.add(SwingSegment(**payload))
        with pytest.raises(IntegrityError):
            session.commit()
