from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict


class TurningPointPayload(BaseModel):
    point_date: date
    point_type: str
    point_price: float


class TurningPointOperationPayload(BaseModel):
    operation_type: str
    old_value: dict[str, Any] | None = None
    new_value: dict[str, Any] | None = None


class TurningPointCommitRequest(BaseModel):
    operator: str | None = None
    operations: list[TurningPointOperationPayload]
    final_points: list[TurningPointPayload]


class StockResearchResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    stock: dict[str, Any]
    prices: list[dict[str, Any]]
    auto_turning_points: list[dict[str, Any]]
    provisional_turning_points: list[dict[str, Any]]
    final_turning_points: list[dict[str, Any]]
    trade_markers: list[dict[str, Any]]
    news_items: list[dict[str, Any]]
    current_state: dict[str, Any]
