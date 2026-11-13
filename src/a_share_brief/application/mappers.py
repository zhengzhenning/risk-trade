"""股池条目与股票聚合之间的映射函数。"""
from __future__ import annotations

from ..domain.aggregates import PoolWindow, Stock, StockBase
from ..domain.services.catalyst import build_logic
from ..domain.services.security import board_of, exchange_of
from ..domain.services.theme_cluster import cluster_themes


def to_base(entry) -> StockBase:
    """股池条目转股票基础数据（仅代码与名称，其余来自基础数据适配器）。

    Args:
        entry: 股池条目。

    Returns:
        最小可用的股票基础数据，交易所按代码前缀推断。
    """
    return StockBase(code=entry.code, name=entry.name,
                     exchange=exchange_of(entry.code), board=board_of(entry.code))




def merge(entry, quoted: Stock | None, alert) -> Stock:
    """合并股池条目、行情与异动，三者互不覆盖。

    Args:
        entry: 股池条目。
        quoted: 行情聚合，可能为 None。
        alert: 异动聚合，可能为 None。

    Returns:
        合并后的股票聚合。
    """
    base = quoted.base if quoted else to_base(entry)
    return Stock(base=base, quote=quoted.quote if quoted else None, alert=alert)


def with_theme(entry, label_of: dict[str, tuple[str, ...]]):
    """把题材标签写入股池条目，供聚类使用。

    Args:
        entry: 股池条目。
        label_of: 代码到题材标签的映射。

    Returns:
        带题材的条目；无标签时保持原样。
    """
    from dataclasses import replace

    labels = label_of.get(entry.code)
    return replace(entry, theme=labels[0]) if labels else entry


def labeled(entries):
    """筛出有题材标签的条目，避免把未识别标的聚成「—」题材。

    Args:
        entries: 股池条目集合。

    Returns:
        题材非空且不为占位符的条目元组。
    """
    return tuple(item for item in entries if item.theme and item.theme != "—")


def build_themes(themes_port, sectors_port, labeled_entries, all_entries):
    """聚类题材并用同行业成分股补全成员。

    Args:
        labeled_entries: 有题材标签的条目。
        all_entries: 全部条目，用于排除已在池内的标的。

    Returns:
        题材元组；未注入板块端口时只含锚点。
    """
    from dataclasses import replace

    from ..domain.aggregates import ThemeMember

    themes = cluster_themes(labeled_entries, PoolWindow.MONTH)
    if not sectors_port or not themes_port:
        return themes

    in_pool = {item.code for item in all_entries}
    # 只扩前三个题材，控制外部请求量（东财板块接口有频控）
    ranked = themes[:3]
    boards = themes_port.sectors_of([item.anchor_code for item in ranked])
    expanded = []
    for theme in ranked:
        board = boards.get(theme.anchor_code)
        if not board:
            expanded.append(theme)
            continue
        peers = [
            ThemeMember(code=code, name=name, via="同行业")
            for code, name in sectors_port.constituents(board, limit=6)
            if code not in in_pool
        ]
        expanded.append(replace(theme, members=theme.members + tuple(peers)))
    return tuple(expanded)


def with_logic(themes, entries):
    """为每个题材补三段式主升逻辑。

    Args:
        themes: 题材元组。
        entries: 当日股池条目。

    Returns:
        带 logic 的题材元组。
    """
    from dataclasses import replace

    return tuple(replace(theme, logic=build_logic(theme, tuple(entries))) for theme in themes)
