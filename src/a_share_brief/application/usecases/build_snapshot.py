"""用例：采集并固化当日快照（写路径）。

幂等约定：同一交易日重跑只递增 revision，不覆盖历史快照。
"""
from __future__ import annotations

import logging
from datetime import date

from ...domain.aggregates import Briefing, PoolRanking, PoolWindow
from ...domain.services.pool import diff
from ...domain.services.wyckoff import judge
from ..mappers import build_themes, labeled, merge, with_logic, with_theme
from ..ports import (
    AlertPort,
    IndexQuotePort,
    KLinePort,
    PoolPort,
    QuotePort,
    SectorPort,
    SnapshotRepo,
    ThemePort,
)

_LOG = logging.getLogger(__name__)


class BuildSnapshot:
    """采集双窗口股池并写入当日快照。

    Args:
        pools: 股池端口（月度前十、近 60 日）
        quotes: 行情端口，用于覆盖实时涨跌与换手
        repo: 快照仓库端口，负责持久化与版本号
    """

    def __init__(
        self,
        pools: PoolPort,
        quotes: QuotePort,
        repo: SnapshotRepo,
        alerts: AlertPort | None = None,
        themes: ThemePort | None = None,
        sectors: SectorPort | None = None,
        klines: KLinePort | None = None,
        indexes: IndexQuotePort | None = None,
        index_codes: tuple[str, ...] = ("000001", "399001", "000688"),
    ) -> None:
        self._pools = pools
        self._quotes = quotes
        self._repo = repo
        self._alerts = alerts
        self._themes = themes
        self._sectors = sectors
        self._klines = klines
        self._indexes = indexes
        self._index_codes = index_codes

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
        label_of = self._themes.themes_of([item.code for item in month_entries + d60_entries]) \
            if self._themes else {}
        month_entries = [with_theme(item, label_of) for item in month_entries]
        d60_entries = [with_theme(item, label_of) for item in d60_entries]
        month_rank = PoolRanking(day=day, window=PoolWindow.MONTH, entries=tuple(month_entries))
        d60_rank = PoolRanking(day=day, window=PoolWindow.D60, entries=tuple(d60_entries))
        stocks = month_entries + d60_entries
        live = self._quotes.snapshot([s.code for s in stocks])
        alerts = self._alerts.unusual([entry.code for entry in stocks]) if self._alerts else {}
        merged = tuple(
            merge(entry, live.get(entry.code), alerts.get(entry.code)) for entry in stocks
        )
        prev = self._repo.load(day)
        revision = prev.revision + 1 if prev else 1
        prev_rank = _ranking_of(prev, PoolWindow.MONTH)
        diffs = (diff(prev_rank, month_rank),)
        index_map = self._indexes.snapshot(self._index_codes, day=day) if self._indexes else {}
        phases = _judge_phases(self._klines, [item.code for item in month_entries[:7]])
        briefing = Briefing(
            day=day,
            rankings=(month_rank, d60_rank),
            diffs=diffs,
            indexes=tuple(index_map[c] for c in self._index_codes if c in index_map),
            stocks=merged,
            phases=phases,
            themes=with_logic(build_themes(self._themes, self._sectors, labeled(month_entries), month_entries),
                              month_entries),
            revision=revision,
        )
        self._repo.save(briefing)
        _LOG.info("snapshot saved day=%s revision=%d pools=%d stocks=%d", day, revision, len(stocks), len(merged))
        return briefing


def _ranking_of(briefing: Briefing | None, window: PoolWindow) -> PoolRanking | None:
    """从历史快照取指定窗口的排名。

    Args:
        briefing: 历史快照，可能为 None。
        window: 目标窗口。

    Returns:
        对应排名；无快照或无该窗口时返回 None。
    """
    if briefing is None:
        return None
    for item in briefing.rankings:
        if item.window is window:
            return item
    return None


def _judge_phases(klines, codes: list[str]) -> dict[str, tuple]:
    """为前七个股判定威科夫阶段。

    Args:
        klines: K 线端口，未注入时返回空。
        codes: 股票代码列表。

    Returns:
        代码到阶段元组的映射。
    """
    if not klines:
        return {}
    out: dict[str, tuple] = {}
    for code in codes:
        try:
            bars = tuple(klines.daily(code, bars=60))
        except (OSError, ValueError):
            continue
        judged = judge(bars)
        if judged:
            out[code] = judged
    return out
