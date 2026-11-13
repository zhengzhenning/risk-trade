"""文件存储适配器：P1 过渡实现，P2 由数据库适配器替换，用例不变。"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..domain.aggregates import Briefing
from .snapshot_codec import (
    index_from_dict,
    index_to_dict,
    ranking_from_dict,
    ranking_to_dict,
    stock_from_dict,
    stock_to_dict,
)


class FileRepoAdapter:
    """把快照读写为单个 JSON 文件。

    Args:
        root: 存储目录，不存在时自动创建。
    """

    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, day: date) -> Path:
        return self.root / f"briefing-{day.isoformat()}.json"

    def save(self, briefing: Briefing) -> None:
        """写入快照，覆盖同一天文件。

        Args:
            briefing: 当日快照。
        """
        payload = {
            "day": briefing.day.isoformat(),
            "revision": briefing.revision,
            "indexes": [index_to_dict(item) for item in briefing.indexes],
            "rankings": [ranking_to_dict(item) for item in briefing.rankings],
            "stocks": [stock_to_dict(item) for item in briefing.stocks],
        }
        self._path(briefing.day).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self, day: date) -> Briefing | None:
        """读取指定交易日快照。

        Args:
            day: 交易日。

        Returns:
            快照；文件不存在返回 None。
        """
        path = self._path(day)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        return Briefing(
            day=day,
            revision=int(payload.get("revision", 1)),
            indexes=tuple(index_from_dict(item) for item in payload.get("indexes", [])),
            rankings=tuple(ranking_from_dict(item) for item in payload.get("rankings", [])),
            stocks=tuple(stock_from_dict(item) for item in payload.get("stocks", [])),
        )
