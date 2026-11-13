"""看板扩展块组装：催化、题材概念、梯队。"""
from __future__ import annotations

from typing import Any

from ..domain.aggregates import Briefing


def build_catalyst(briefing: Briefing) -> dict[str, Any]:
    """主升催化：锚点主块 + 行业/资金背景行（字段对齐模板）。"""
    out: dict[str, Any] = {}
    for theme in briefing.themes:
        logic = theme.logic
        chain = []
        if logic and logic.trigger:
            chain.append(f"触发：{logic.trigger}")
        if logic and logic.diffusion:
            chain.append(f"扩散：{logic.diffusion}")
        if logic and logic.positioning:
            chain.append(f"卡位：{logic.positioning}")
        rows: list[dict[str, Any]] = [{
            "kind": "main",
            "core": (logic.trigger if logic else "") or theme.narrative or theme.name,
            "chain": chain,
            "evid": "；".join(logic.evidence) if logic else "",
            "risk": "",
        }]
        if logic and logic.diffusion:
            rows.append({"tag": "行业", "t": logic.diffusion, "n": logic.positioning})
        if logic and logic.evidence:
            rows.append({"tag": "资金", "t": "；".join(logic.evidence[:2]), "n": ""})
        out[theme.anchor_code] = rows
    return out


def build_concepts(briefing: Briefing, theme_of: dict[str, str]) -> dict[str, Any]:
    """个股题材与行业标签。"""
    out: dict[str, Any] = {}
    for stock in briefing.stocks:
        theme = theme_of.get(stock.base.code)
        labels = [label for label in stock.base.themes if label]
        if theme and theme not in labels:
            labels.append(theme)
        out[stock.base.code] = {
            "name": stock.base.name,
            "industry": list(stock.base.industry),
            "concepts": labels,
        }
    return out


def build_tiers(briefing: Briefing) -> dict[str, Any]:
    """题材梯队：成员与名次。"""
    out: dict[str, Any] = {}
    for theme in briefing.themes:
        out[theme.name] = [
            {"code": m.code, "name": m.name, "mp": round(m.range_pct, 2),
             "anchor": m.is_anchor, "rk": m.rank_in_pool}
            for m in theme.members
        ]
    return out
