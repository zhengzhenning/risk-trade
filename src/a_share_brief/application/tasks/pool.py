"""股池采集用例。"""
from __future__ import annotations


def collect(pool) -> list[dict]:
    """采集月度与近 60 日排名。

    Args:
        pool: 股池端口。

    Returns:
        两个窗口的名次列表。
    """
    month, d60 = pool.month_top(10), pool.d60_top(7)
    return [{"window": "MONTH", "entries": [(e.rank, e.code, e.name, e.range_pct) for e in month]},
            {"window": "D60", "entries": [(e.rank, e.code, e.name, e.range_pct) for e in d60]}]
