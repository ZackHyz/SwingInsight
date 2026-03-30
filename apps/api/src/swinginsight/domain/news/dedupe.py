from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Any


def normalize_title(title: str) -> str:
    return " ".join(title.lower().split())


def dedupe_news_items(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, str, date | None], dict[str, Any]] = {}
    for item in items:
        key = (
            normalize_title(str(item.get("title", ""))),
            str(item.get("source_name", "")),
            item.get("news_date"),
        )
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = item
            continue

        existing_id = int(existing.get("id", 0) or 0)
        current_id = int(item.get("id", 0) or 0)
        if current_id < existing_id or existing_id == 0:
            grouped[key] = item
    return list(grouped.values())
