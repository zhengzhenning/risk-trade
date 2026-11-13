"""主升逻辑：由题材与股池事实归纳「触发 → 扩散 → 卡位」。

只做事实拼接，不编造：每段都必须能回指股池名次或成员涨幅。
"""
from __future__ import annotations

from ..aggregates import MainUpLogic, PoolEntry, Theme


def build_logic(theme: Theme, entries: tuple[PoolEntry, ...]) -> MainUpLogic:
    """归纳题材主升逻辑。

    Args:
        theme: 题材聚合（含锚点与成员）。
        entries: 当日前七条目，用于取锚点区间涨幅。

    Returns:
        三段式逻辑与证据；信息不足的段落留空字符串。
    """
    anchor = next((item for item in entries if item.code == theme.anchor_code), None)
    rank = theme.rank
    range_pct = anchor.range_pct if anchor else 0.0
    peers = [member for member in theme.members if not member.is_anchor]

    trigger = (
        f"{theme.anchor_name} 位列#{rank}，窗口涨幅 {range_pct:+.2f}%"
        if anchor else f"{theme.anchor_name} 为题材锚点"
    ) if range_pct else f"{theme.anchor_name} 位列#{rank}"

    if peers:
        top = "、".join(member.name for member in peers[:3])
        diffusion = f"{theme.sector or theme.name} 同行业 {len(peers)} 只跟随：{top}"
    else:
        diffusion = f"{theme.sector or theme.name} 暂无同行业跟随"

    positioning = f"{theme.name} 锚点#{rank}，题材内共 {len(theme.members)} 只"
    evidence = tuple(
        f"{member.name}({member.code}) {member.rank_in_pool or '-'}"
        for member in theme.members[:5]
    )
    return MainUpLogic(
        trigger=trigger,
        diffusion=diffusion,
        positioning=positioning,
        evidence=evidence,
    )
