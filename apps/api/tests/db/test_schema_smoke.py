from datetime import date
from pathlib import Path
import sys

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def test_daily_price_unique_constraint() -> None:
    from swinginsight.db.base import Base
    from swinginsight.db.models.market_data import DailyPrice

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)

    with Session() as session:
        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 2),
                open_price=10,
                high_price=11,
                low_price=9,
                close_price=10.5,
                adj_type="qfq",
            )
        )
        session.commit()

        session.add(
            DailyPrice(
                stock_code="000001",
                trade_date=date(2024, 1, 2),
                open_price=10,
                high_price=11,
                low_price=9,
                close_price=10.5,
                adj_type="qfq",
            )
        )
        with pytest.raises(IntegrityError):
            session.commit()


def test_segment_uid_length_supports_algorithm_version_suffix() -> None:
    from swinginsight.db.models.segment import SwingSegment

    assert SwingSegment.__table__.c.segment_uid.type.length >= 128
