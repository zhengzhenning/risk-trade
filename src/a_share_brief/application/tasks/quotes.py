"""行情采集用例。"""
from __future__ import annotations

from collections.abc import Sequence


def collect(quotes, codes: Sequence[str]) -> list[dict]:
    """采集实时行情。

    Args:
        quotes: 行情端口。
        codes: 标的代码。

    Returns:
        代码与涨跌幅列表。
    """
    if not codes:
        return []
    rows = quotes.snapshot(codes)
    return [{"code": code, "pct": round(stock.quote.pct, 2) if stock.quote else None}
            for code, stock in rows.items()]
