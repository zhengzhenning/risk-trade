"""视图转换：把领域聚合转成接口可直接序列化的结构。"""
from __future__ import annotations

from typing import Any

from ..domain.aggregates import PoolMatrix, RankCell


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
