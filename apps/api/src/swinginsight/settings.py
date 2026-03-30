from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class Settings:
    app_name: str = "SwingInsight API"

    @classmethod
    def model_validate(cls, data: dict[str, Any]) -> "Settings":
        return cls(**data)
