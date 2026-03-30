from dataclasses import dataclass
import os
from typing import Any


@dataclass(slots=True)
class Settings:
    app_name: str = "SwingInsight API"
    database_url: str = "postgresql+psycopg://swinginsight:swinginsight@127.0.0.1:5432/swinginsight"

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
        }
        env_data.update(data)
        return cls(**env_data)
