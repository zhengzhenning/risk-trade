"""题材聚合的序列化：与快照编解码分离，控制单文件规模。"""
from __future__ import annotations

from typing import Any

from ..domain.aggregates import MainUpLogic, PoolWindow, Theme, ThemeMember, ThemeStatus


def theme_to_dict(theme: Theme) -> dict[str, Any]:
    """题材聚合转字典。

    Args:
        theme: 题材聚合。

    Returns:
        含锚点、成员与叙述的字典。
    """
    return {
        "id": theme.id,
        "name": theme.name,
        "anchor_code": theme.anchor_code,
        "anchor_name": theme.anchor_name,
        "window": theme.window.value,
        "rank": theme.rank,
        "sector": theme.sector,
        "status": theme.status.value,
        "narrative": theme.narrative,
        "logic": (
            {"trigger": theme.logic.trigger, "diffusion": theme.logic.diffusion,
             "positioning": theme.logic.positioning, "evidence": list(theme.logic.evidence)}
            if theme.logic else None
        ),
        "members": [
            {"code": m.code, "name": m.name, "is_anchor": m.is_anchor,
             "rank_in_pool": m.rank_in_pool, "range_pct": m.range_pct,
             "limit_up_days": m.limit_up_days}
            for m in theme.members
        ],
    }


def theme_from_dict(payload: dict[str, Any]) -> Theme:
    """字典还原题材聚合。

    Args:
        payload: theme_to_dict 的输出。

    Returns:
        题材聚合。
    """
    members = tuple(
        ThemeMember(code=m["code"], name=m["name"], is_anchor=bool(m.get("is_anchor")),
                    rank_in_pool=m.get("rank_in_pool"), range_pct=m.get("range_pct", 0.0),
                    limit_up_days=int(m.get("limit_up_days", 0)))
        for m in payload.get("members", [])
    )
    return Theme(
        id=payload["id"],
        name=payload["name"],
        anchor_code=payload.get("anchor_code", ""),
        anchor_name=payload.get("anchor_name", ""),
        window=PoolWindow(payload.get("window", "MONTH")),
        rank=int(payload.get("rank", 99)),
        sector=payload.get("sector", ""),
        status=ThemeStatus(payload.get("status", "BREWING")),
        narrative=payload.get("narrative", ""),
        members=members,
        logic=(
            MainUpLogic(**{**payload["logic"], "evidence": tuple(payload["logic"].get("evidence", []))})
            if payload.get("logic") else None
        ),
    )
