"""题材标签缓存：抓取失败时回退到最近一次非空结果。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_ROOT = Path("work/cache")


def save(day: str, labels: dict[str, list[str]]) -> None:
    """写入当日标签缓存。

    Args:
        day: 交易日（ISO）。
        labels: 代码到标签列表。
    """
    if not labels:
        return
    _ROOT.mkdir(parents=True, exist_ok=True)
    (_ROOT / f"labels-{day}.json").write_text(
        json.dumps(labels, ensure_ascii=False), encoding="utf-8")


def load_latest(day: str, include_today: bool = True) -> dict[str, Any]:
    """读取最近一份非空缓存（不含当日）。

    Args:
        day: 当前交易日，用于跳过当日文件。

    Returns:
        代码到标签列表；无缓存返回空字典。
    """
    files = sorted(_ROOT.glob("labels-*.json"))
    for path in reversed(files):
        if not include_today and day in path.name:
            continue
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        if payload:
            return payload
    return {}
