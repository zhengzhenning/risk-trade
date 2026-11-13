"""题材聚类：以股池龙头为锚点，带出成员与主升逻辑。"""
from __future__ import annotations

from ..aggregates import PoolEntry, PoolWindow, StockRole, Theme, ThemeMember


def cluster_themes(entries: tuple[PoolEntry, ...], window: PoolWindow,
                   sector_of: dict[str, str] | None = None) -> tuple[Theme, ...]:
    """以涨幅龙头为锚点聚类题材（以点带面）。

    规则：
        1. 同一窗口的 TOP7 按题材分组，组内名次最高者为锚定龙头；
        2. 组内其余标的成为成员（跟风/梯队），名次与区间涨幅随行；
        3. 题材按锚点名次升序排列，保证与榜单顺序一致。

    Args:
        entries: 同一窗口的排名条目（通常前七）。
        window: 窗口枚举。
        sector_of: 代码到东财行业的映射，用于板块效应载体。

    Returns:
        题材列表，每个题材带锚点、成员与板块名。
    """
    groups: dict[str, list[PoolEntry]] = {}
    for e in entries:
        groups.setdefault(e.theme or "—", []).append(e)

    themes: list[Theme] = []
    for name, rows in groups.items():
        rows = sorted(rows, key=lambda r: r.rank)
        anchor = rows[0]
        members = tuple(
            ThemeMember(
                code=r.code,
                name=r.name,
                role=StockRole.ANCHOR if r.code == anchor.code else StockRole.FOLLOW,
                is_anchor=r.code == anchor.code,
                rank_in_pool=r.rank,
                range_pct=r.range_pct,
                limit_up_days=max(0, int(r.consecutive_limit_up)) if hasattr(r, "consecutive_limit_up") else 0,
                via="同题材且进入窗口前七",
            )
            for r in rows
        )
        themes.append(Theme(
            id=name,
            name=name,
            anchor_code=anchor.code,
            anchor_name=anchor.name,
            window=window,
            rank=anchor.rank,
            sector=(sector_of or {}).get(anchor.code, ""),
            members=members,
        ))
    return tuple(sorted(themes, key=lambda t: t.rank))
