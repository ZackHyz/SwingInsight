from __future__ import annotations

import re


def normalize_title(title: str) -> str:
    compact = re.sub(r"\s+", " ", title.strip().lower())
    return compact


def build_title_signature(title: str) -> str:
    normalized = normalize_title(title)
    return re.sub(r"[^0-9a-z\u4e00-\u9fff]+", "", normalized)
