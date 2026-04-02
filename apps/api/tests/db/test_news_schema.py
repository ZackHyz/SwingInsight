from pathlib import Path
import sys

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker


sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))


def build_inspector():
    from swinginsight.db.base import Base
    from swinginsight.db.models import news as _news_models  # noqa: F401

    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Session = sessionmaker(bind=engine, future=True)
    Base.metadata.create_all(engine)
    return inspect(engine), Session


def test_news_schema_includes_processed_and_point_mapping_tables() -> None:
    inspector, _ = build_inspector()

    table_names = set(inspector.get_table_names())

    assert "news_processed" in table_names
    assert "point_news_map" in table_names


def test_news_raw_includes_processing_columns() -> None:
    inspector, _ = build_inspector()

    columns = {column["name"] for column in inspector.get_columns("news_raw")}

    assert "raw_json" in columns
    assert "fetch_time" in columns
    assert "is_parsed" in columns
    assert "parse_status" in columns
    assert "main_news_id" in columns
