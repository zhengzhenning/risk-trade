"""题材采集用例。"""
from __future__ import annotations

from collections.abc import Sequence


def collect(themes, codes: Sequence[str]) -> list[dict]:
    """采集题材标签。

    Args:
        themes: 题材端口。
        codes: 标的代码。

    Returns:
        代码与标签列表。
    """
    rows = themes.themes_of(codes)
    return [{"code": code, "labels": list(labels)} for code, labels in rows.items()]
