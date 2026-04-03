from dataclasses import dataclass, field
import os
from typing import Any

from swinginsight.ingest.source_priority import parse_priority


def _default_daily_price_priority() -> list[str]:
    return ["akshare", "tushare", "mootdx"]


@dataclass(slots=True)
class Settings:
    app_name: str = "SwingInsight API"
    database_url: str = "postgresql+psycopg://swinginsight:swinginsight@127.0.0.1:5432/swinginsight"
    data_source_priority_daily_price: list[str] = field(default_factory=_default_daily_price_priority)
    data_source_priority_metadata: list[str] = field(default_factory=_default_daily_price_priority)
    tushare_token: str | None = None

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "Settings":
        env_data = {
            "app_name": os.getenv("APP_NAME", "SwingInsight API"),
            "database_url": os.getenv(
                "DATABASE_URL",
                (
                    "postgresql+psycopg://"
                    f"{os.getenv('POSTGRES_USER', 'swinginsight')}:"
                    f"{os.getenv('POSTGRES_PASSWORD', 'swinginsight')}@"
                    f"{os.getenv('POSTGRES_HOST', '127.0.0.1')}:"
                    f"{os.getenv('POSTGRES_PORT', '5432')}/"
                    f"{os.getenv('POSTGRES_DB', 'swinginsight')}"
                ),
            ),
            "data_source_priority_daily_price": parse_priority(
                os.getenv("DATA_SOURCE_PRIORITY_DAILY_PRICE"),
                _default_daily_price_priority(),
            ),
            "data_source_priority_metadata": parse_priority(
                os.getenv("DATA_SOURCE_PRIORITY_METADATA"),
                _default_daily_price_priority(),
            ),
            "tushare_token": os.getenv("TUSHARE_TOKEN"),
        }
        env_data.update(data)
        return cls(**env_data)
