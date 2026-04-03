from __future__ import annotations

from datetime import date, datetime

try:
    import akshare as ak
except ModuleNotFoundError:  # pragma: no cover - exercised in tests via monkeypatch
    ak = None


def _to_records(frame: object) -> list[dict[str, object]]:
    if frame is None:
        return []
    to_dict = getattr(frame, "to_dict", None)
    if callable(to_dict):
        return list(to_dict("records"))
    if isinstance(frame, list):
        return [dict(row) for row in frame]
    return []


def _parse_publish_time(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


class EastmoneyNewsFeed:
    def fetch_news(self, stock_code: str, start: date | None, end: date | None):
        if ak is None:
            raise ModuleNotFoundError("akshare is required for EastmoneyNewsFeed")
        rows: list[dict[str, object]] = []
        for record in _to_records(ak.stock_news_em(symbol=stock_code)):
            publish_time = _parse_publish_time(record.get("发布时间"))
            if publish_time is None:
                continue
            news_date = publish_time.date()
            if start is not None and news_date < start:
                continue
            if end is not None and news_date > end:
                continue

            url = str(record.get("新闻链接") or "").strip()
            rows.append(
                {
                    "news_uid": f"eastmoney:{stock_code}:{url}" if url else None,
                    "stock_code": stock_code,
                    "title": record.get("新闻标题"),
                    "summary": record.get("新闻内容"),
                    "content": record.get("新闻内容"),
                    "publish_time": publish_time,
                    "news_date": news_date,
                    "source_name": record.get("文章来源") or "eastmoney",
                    "source_type": "media_news",
                    "url": url or None,
                    "raw_json": dict(record),
                    "data_source": "eastmoney",
                }
            )
        return rows
