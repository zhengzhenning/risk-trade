"""视图转换：把领域聚合转成接口可直接序列化的结构。"""
from __future__ import annotations

from typing import Any

from ..domain.aggregates import PoolMatrix, RankCell, Theme


def _cell(item: RankCell | None) -> dict[str, Any] | None:
    if item is None:
        return None
    return {
        "day": item.day.isoformat(),
        "rank": item.rank,
        "code": item.code,
        "name": item.name,
        "range_pct": item.range_pct,
        "is_new": item.is_new,
    }


def _rows(lines) -> list[dict[str, Any]]:
    return [
        {"rank": index + 1, "cells": [_cell(item) for item in line]}
        for index, line in enumerate(lines)
    ]


def matrix_to_dict(matrix: PoolMatrix) -> dict[str, Any]:
    """把股池矩阵转成行列结构。

    Args:
        matrix: 领域矩阵聚合。

    Returns:
        含 dates/rows/tail 的字典，单元格为空表示该名次当日无标的。
    """
    return {
        "window": matrix.window.value,
        "dates": [day.isoformat() for day in matrix.dates],
        "today": matrix.today.isoformat() if matrix.today else None,
        "rows": _rows(matrix.rows),
        "tail": _rows(matrix.tail),
    }


def theme_to_view(theme: Theme) -> dict[str, Any]:
    """题材聚合转接口视图。

    Args:
        theme: 题材聚合。

    Returns:
        含锚点、成员与叙述的字典。
    """
    return {
        "id": theme.id,
        "name": theme.name,
        "anchor": {"code": theme.anchor_code, "name": theme.anchor_name, "rank": theme.rank},
        "window": theme.window.value,
        "status": theme.status.value,
        "narrative": theme.narrative,
        "logic": (
            {"trigger": theme.logic.trigger, "diffusion": theme.logic.diffusion,
             "positioning": theme.logic.positioning, "evidence": list(theme.logic.evidence)}
            if theme.logic else None
        ),
        "members": [
            {"code": m.code, "name": m.name, "is_anchor": m.is_anchor,
             "rank_in_pool": m.rank_in_pool, "range_pct": m.range_pct}
            for m in theme.members
        ],
    }
