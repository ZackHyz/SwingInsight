from __future__ import annotations


class TushareMetadataFeed:
    def fetch_stock_metadata(self, stock_code: str):
        raise NotImplementedError("Tushare metadata integration will be wired in a later task.")
