"""动态股池：窗口、排名、差异与矩阵。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum


class PoolWindow(str, Enum):
    """动态股池窗口。"""

    MONTH = "MONTH"   # 月度前十（矩阵展示前七，榜外 8-10）
    D60 = "D60"       # 近 60 个交易日涨幅前七


@dataclass(frozen=True)
class PoolEntry:
    """股池条目：某窗口某名次的标的。

    Attributes:
        code: 标的代码。
        name: 简称。
        rank: 名次，1 开始。
        window: 所属窗口（月度前十 / 近 60 日前七）。
        range_pct: 窗口区间涨跌幅（%）。
        pct: 当日涨跌幅（%）。
        turnover: 换手率（%）。
        auction_pct: 集合竞价涨跌幅（%）。
        theme: 题材名（矩阵与面板共用）。
        is_top: 是否同时命中另一窗口（★最强）。
    """

    code: str
    name: str
    rank: int
    window: PoolWindow = PoolWindow.MONTH
    range_pct: float = 0.0
    pct: float = 0.0
    turnover: float = 0.0
    auction_pct: float = 0.0
    theme: str = "—"
    is_top: bool = False


@dataclass(frozen=True)
class PoolRanking:
    """某交易日的股池排名快照（不可变）。

    Attributes:
        day: 交易日。
        window: 窗口。
        entries: 按名次升序的条目。
        captured_at: 抓取时间戳。
        baseline: 是否首次记录（无对比基线）。
        note: 数据质量标记，如「接口未返回第 3 名」。
    """

    day: date
    window: PoolWindow
    entries: tuple[PoolEntry, ...]
    captured_at: str = ""
    baseline: bool = False
    note: str = ""

    def __post_init__(self) -> None:
        """校验名次唯一且升序，越界条目直接拒绝。"""
        ranks = [e.rank for e in self.entries]
        if ranks != sorted(ranks) or len(set(ranks)) != len(ranks):
            raise ValueError(f"股池名次必须唯一升序: day={self.day} window={self.window}")

    def top(self, n: int) -> tuple[PoolEntry, ...]:
        """取前 n 名。

        Args:
            n: 名次上限。

        Returns:
            名次 1..n 的条目，不足 n 时返回现有条目。
        """
        return tuple(e for e in self.entries if e.rank <= n)


@dataclass(frozen=True)
class PoolDiff:
    """与上一交易日的排名差异。

    Attributes:
        window: 窗口。
        day: 当日。
        prev_day: 对比基准日（最近一个不同交易日）。
        added: 新进条目。
        removed: 移出条目（携带上一名次）。
        retained: 留存条目。
    """

    window: PoolWindow
    day: date
    prev_day: date | None
    added: tuple[PoolEntry, ...] = ()
    removed: tuple[PoolEntry, ...] = ()
    retained: tuple[PoolEntry, ...] = ()


@dataclass(frozen=True)
class RankCell:
    """矩阵单元格：某日某名次的标的事实。

    Attributes:
        day: 交易日。
        rank: 名次。
        code: 代码。
        name: 简称。
        range_pct: 该窗口区间涨跌幅（%）。
        is_new: 是否首次进入该名次（相对前一列）。
    """

    day: date
    rank: int
    code: str
    name: str
    range_pct: float = 0.0
    is_new: bool = False


@dataclass(frozen=True)
class PoolMatrix:
    """股池当月矩阵：行=名次，列=交易日。

    Attributes:
        window: 窗口。
        dates: 列（升序）。
        rows: 前七行，每行按 dates 对齐的单元格。
        tail: 榜外 8-10 行。
        today: 当日列。
    """

    window: PoolWindow
    dates: tuple[date, ...]
    rows: tuple[tuple[RankCell | None, ...], ...]
    tail: tuple[tuple[RankCell | None, ...], ...] = ()
    today: date | None = None


@dataclass(frozen=True)
class Bar:
    """日 K 线。"""

    day: str
    open: float
    close: float
    low: float
    high: float
    volume: float
    pct: float
    turnover: float = 0.0
