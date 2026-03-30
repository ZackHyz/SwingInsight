from __future__ import annotations

from datetime import date


class AkshareNewsFeed:
    def fetch_news(self, stock_code: str, start: date | None, end: date | None):
        raise NotImplementedError("AkShare news integration will be wired in a later task.")
