"""股池纯函数：排名差分与矩阵组装。

不依赖端口与 IO，输入是历史排名快照，输出是差异与矩阵视图。
"""
from __future__ import annotations

from datetime import date

from ..aggregates import PoolDiff, PoolEntry, PoolMatrix, PoolRanking, RankCell


def diff(prev: PoolRanking | None, curr: PoolRanking, top_n: int = 7) -> PoolDiff:
    """对比两个交易日的排名。

    Args:
        prev: 上一交易日排名，首次记录时为 None。
        curr: 当日排名。
        top_n: 参与对比的名次上限（默认前七）。

    Returns:
        新增/移出/留存条目；prev 为 None 时 added 等于当日全部、removed 为空。
    """
    cur_top = curr.top(top_n)
    if prev is None:
        return PoolDiff(window=curr.window, day=curr.day, prev_day=None,
                        added=cur_top, removed=(), retained=())
    prev_top = prev.top(top_n)
    cur_codes = {e.code for e in cur_top}
    prev_codes = {e.code for e in prev_top}
    return PoolDiff(
        window=curr.window,
        day=curr.day,
        prev_day=prev.day,
        added=tuple(e for e in cur_top if e.code not in prev_codes),
        removed=tuple(e for e in prev_top if e.code not in cur_codes),
        retained=tuple(e for e in cur_top if e.code in prev_codes),
    )


def matrix(rankings: list[PoolRanking], window, top_n: int = 7, tail_n: int = 10) -> PoolMatrix:
    """按交易日组装矩阵。

    Args:
        rankings: 同一窗口的历史排名，可乱序。
        window: 窗口枚举。
        top_n: 前列行数（默认 7）。
        tail_n: 含榜外的总行数上限（默认 10）。

    Returns:
        行=名次、列=交易日的矩阵；缺失格为 None。
    """
    ordered = sorted(rankings, key=lambda r: r.day)
    dates = tuple(r.day for r in ordered)
    by_date = {r.day: {e.rank: e for e in r.entries} for r in ordered}

    def cell(day: date, rank: int, prev_cell: RankCell | None) -> RankCell | None:
        entry: PoolEntry | None = by_date.get(day, {}).get(rank)
        if entry is None:
            return None
        return RankCell(day=day, rank=rank, code=entry.code, name=entry.name,
                        range_pct=entry.range_pct,
                        is_new=bool(prev_cell and prev_cell.code != entry.code))

    rows = []
    for rank in range(1, top_n + 1):
        line: list[RankCell | None] = []
        for i, day in enumerate(dates):
            line.append(cell(day, rank, line[i - 1] if i else None))
        rows.append(tuple(line))

    tail = []
    for rank in range(top_n + 1, tail_n + 1):
        line = []
        for i, day in enumerate(dates):
            line.append(cell(day, rank, line[i - 1] if i else None))
        tail.append(tuple(line))

    return PoolMatrix(window=window, dates=dates, rows=tuple(rows),
                      tail=tuple(tail), today=dates[-1] if dates else None)
