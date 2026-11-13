"""用例：采集并固化当日快照（写路径）。

幂等约定：同一交易日重跑只递增 revision，不覆盖历史快照。
"""
from __future__ import annotations

import logging
from datetime import date

from ...domain.aggregates import Briefing, PoolRanking, PoolWindow, Stock, StockBase
from ...domain.services.pool import diff
from ...domain.services.security import board_of, exchange_of
from ..ports import PoolPort, QuotePort, SnapshotRepo

_LOG = logging.getLogger(__name__)


class BuildSnapshot:
    """采集双窗口股池并写入当日快照。

    Args:
        pools: 股池端口（月度前十、近 60 日）
        quotes: 行情端口，用于覆盖实时涨跌与换手
        repo: 快照仓库端口，负责持久化与版本号
    """

    def __init__(self, pools: PoolPort, quotes: QuotePort, repo: SnapshotRepo) -> None:
        self._pools = pools
        self._quotes = quotes
        self._repo = repo

    def __call__(self, day: date) -> Briefing:
        """构建并保存快照。

        Args:
            day: 交易日。

        Returns:
            已保存的快照，revision 为本次写入版本。

        Raises:
            Exception: 适配器抛出的外部错误原样上抛，由调度器记录 job_run。
        """
        month_entries = self._pools.month_top(10)
        d60_entries = self._pools.d60_top(7)
        month_rank = PoolRanking(day=day, window=PoolWindow.MONTH, entries=tuple(month_entries))
        d60_rank = PoolRanking(day=day, window=PoolWindow.D60, entries=tuple(d60_entries))
        stocks = month_entries + d60_entries
        live = self._quotes.snapshot([s.code for s in stocks])
        merged = tuple(live.get(entry.code) or Stock(base=_to_base(entry)) for entry in stocks)
        prev = self._repo.load(day)
        revision = prev.revision + 1 if prev else 1
        prev_rank = _ranking_of(prev, PoolWindow.MONTH)
        diffs = (diff(prev_rank, month_rank),)
        briefing = Briefing(day=day, rankings=(month_rank, d60_rank), diffs=diffs,
                            stocks=merged, revision=revision)
        self._repo.save(briefing)
        _LOG.info("snapshot saved day=%s revision=%d pools=%d stocks=%d", day, revision, len(stocks), len(merged))
        return briefing


def _to_base(entry) -> StockBase:
    """股池条目转股票基础数据（仅代码与名称，其余来自基础数据适配器）。

    Args:
        entry: 股池条目。

    Returns:
        最小可用的股票基础数据，交易所按代码前缀推断。
    """
    return StockBase(code=entry.code, name=entry.name,
                     exchange=exchange_of(entry.code), board=board_of(entry.code))




def _ranking_of(briefing: Briefing | None, window: PoolWindow) -> PoolRanking | None:
    """从历史快照取指定窗口的排名。

    Args:
        briefing: 历史快照，可能为 None。
        window: 目标窗口。

    Returns:
        对应排名；快照为空或无该窗口时返回 None。
    """
    if briefing is None:
        return None
    for item in briefing.rankings:
        if item.window is window:
            return item
    return None
