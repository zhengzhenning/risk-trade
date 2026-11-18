"""分片存储：每个采集任务只写自己的文件，带采集时间。"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


def save(root: Path, name: str, rows: list[dict[str, Any]]) -> None:
    """写入一个分片。

    Args:
        root: 分片根目录。
        name: 分片名（quotes/index/pool/alert/theme）。
        rows: 采集结果。
    """
    if not rows:
        # 统一策略：空结果不覆盖最近一次成功值
        return
    target = Path(root) / f"{name}.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {"captured_at": datetime.now().isoformat(timespec="seconds"), "rows": rows}
    target.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load(root: Path, name: str) -> dict[str, Any] | None:
    """读取分片。

    Args:
        root: 分片根目录。
        name: 分片名。

    Returns:
        分片内容；不存在或损坏返回 None。
    """
    target = Path(root) / f"{name}.json"
    if not target.exists():
        return None
    try:
        return json.loads(target.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
