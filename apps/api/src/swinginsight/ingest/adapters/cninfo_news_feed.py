from __future__ import annotations

from datetime import date, datetime, timedelta
import hashlib
from urllib.parse import parse_qs, urlparse

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


def _parse_notice_time(value: object) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, str):
        for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(value.strip(), pattern)
            except ValueError:
                continue
    return None


def _build_news_uid(stock_code: str, url: str | None, title: object, publish_time: datetime | None) -> str | None:
    if url:
        query = parse_qs(urlparse(url).query)
        announcement_id = next(iter(query.get("announcementId", [])), "").strip()
        if announcement_id:
            return f"cninfo:{stock_code}:{announcement_id}"
        return f"cninfo:{stock_code}:{hashlib.sha1(url.encode('utf-8')).hexdigest()[:16]}"

    fallback_seed = f"{stock_code}|{publish_time.isoformat() if publish_time else ''}|{title or ''}"
    if fallback_seed.strip("|"):
        return f"cninfo:{stock_code}:{hashlib.sha1(fallback_seed.encode('utf-8')).hexdigest()[:16]}"
    return None


class CninfoNewsFeed:
    def fetch_news(self, stock_code: str, start: date | None, end: date | None):
        if ak is None:
            raise ModuleNotFoundError("akshare is required for CninfoNewsFeed")
        resolved_end = end or date.today()
        resolved_start = start or (resolved_end - timedelta(days=7))

        rows: list[dict[str, object]] = []
        for record in _to_records(
            ak.stock_zh_a_disclosure_report_cninfo(
                symbol=stock_code,
                market="沪深京",
                keyword="",
                category="",
                start_date=resolved_start.strftime("%Y%m%d"),
                end_date=resolved_end.strftime("%Y%m%d"),
            )
        ):
            publish_time = _parse_notice_time(record.get("公告时间"))
            if publish_time is None:
                continue
            news_date = publish_time.date()
            if news_date < resolved_start or news_date > resolved_end:
                continue

            url = str(record.get("公告链接") or "").strip()
            rows.append(
                {
                    "news_uid": _build_news_uid(stock_code, url or None, record.get("公告标题"), publish_time),
                    "stock_code": stock_code,
                    "title": record.get("公告标题"),
                    "summary": None,
                    "content": None,
                    "publish_time": publish_time,
                    "news_date": news_date,
                    "source_name": "cninfo",
                    "source_type": "announcement",
                    "url": url or None,
                    "raw_json": dict(record),
                    "data_source": "cninfo",
                }
            )
        return rows
