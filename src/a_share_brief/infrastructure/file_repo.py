"""文件存储适配器：P1 过渡实现（后续替换为 PgRepoAdapter，用例不改）。"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from ..domain.aggregates import Briefing, Stock


class FileRepoAdapter:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, day: date) -> Path:
        return self.root / f"briefing-{day.isoformat()}.json"

    def save(self, briefing: Briefing) -> None:
        payload = {
            "day": briefing.day.isoformat(),
            "revision": briefing.revision,
            "stocks": [s.__dict__ for s in briefing.stocks],
        }
        self._path(briefing.day).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def load(self, day: date) -> Briefing | None:
        p = self._path(day)
        if not p.exists():
            return None
        data = json.loads(p.read_text(encoding="utf-8"))
        stocks = tuple(Stock(**s) for s in data.get("stocks", []))
        return Briefing(day=day, stocks=stocks, revision=data.get("revision", 1))
