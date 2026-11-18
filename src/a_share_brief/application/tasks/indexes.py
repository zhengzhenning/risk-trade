"""指数采集用例。"""
from __future__ import annotations


def collect(indexes) -> list[dict]:
    """采集三大指数。

    Args:
        indexes: 指数端口。

    Returns:
        名称、收盘、涨跌幅列表。
    """
    rows = indexes.snapshot(["000001", "399001", "000688"])
    return [{"name": item.base.name,
             "close": item.quote.close if item.quote else None,
             "pct": item.quote.change_pct if item.quote else None}
            for item in rows.values()]
