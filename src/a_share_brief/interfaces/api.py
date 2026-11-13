"""HTTP 接口层：只做参数解析与快照读取，不写业务规则。

运行环境为 Python 3.9，FastAPI 会在运行时解析注解，故保留 Optional 写法。
"""
from __future__ import annotations

import os
import time
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse

from ..domain.aggregates import PoolWindow
from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.snapshot_codec import (
    index_to_dict,
    ranking_to_dict,
    stock_to_dict,
)

_WINDOWS = {"MONTH": PoolWindow.MONTH, "D60": PoolWindow.D60}


def _available_days(root: Path) -> list[date]:
    days = []
    for path in root.glob("briefing-*.json"):
        try:
            days.append(date.fromisoformat(path.stem.removeprefix("briefing-")))
        except ValueError:
            continue
    return sorted(days)


def create_app(store_root: Optional[Path] = None) -> FastAPI:
    """创建 HTTP 应用。

    Args:
        store_root: 快照存储目录；缺省读环境变量 ``BRIEF_STORE``，再缺省 ``work/store``。

    Returns:
        FastAPI 应用实例。
    """
    root = Path(store_root or os.environ.get("BRIEF_STORE", "work/store"))
    app = FastAPI(title="A 股每日看板", version="0.1.0")
    repo = FileRepoAdapter(root)

    def _resolve(day: Optional[str]) -> date:
        if day:
            try:
                return date.fromisoformat(day)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=f"日期格式错误: {day}") from exc
        days = _available_days(root)
        if not days:
            raise HTTPException(status_code=404, detail="暂无快照")
        return days[-1]

    @app.get("/healthz")
    def healthz() -> dict:
        days = _available_days(root)
        return {"status": "ok", "days": len(days), "latest": days[-1].isoformat() if days else None}

    @app.get("/api/history")
    def history() -> dict:
        return {"days": [d.isoformat() for d in _available_days(root)]}

    @app.get("/api/briefing")
    def briefing(day: Optional[str] = Query(None, alias="date")) -> dict:
        target = _resolve(day)
        snapshot = repo.load(target)
        if snapshot is None:
            raise HTTPException(status_code=404, detail=f"无 {target} 快照")
        return {
            "day": snapshot.day.isoformat(),
            "revision": snapshot.revision,
            "indexes": [index_to_dict(item) for item in snapshot.indexes],
            "rankings": [ranking_to_dict(item) for item in snapshot.rankings],
            "stocks": [stock_to_dict(item) for item in snapshot.stocks],
        }

    @app.get("/api/pool/{window}")
    def pool(window: str, day: Optional[str] = Query(None, alias="date")) -> dict:
        target_window = _WINDOWS.get(window.upper())
        if target_window is None:
            raise HTTPException(status_code=400, detail=f"未知窗口: {window}")
        snapshot = repo.load(_resolve(day))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="无快照")
        for ranking in snapshot.rankings:
            if ranking.window is target_window:
                return ranking_to_dict(ranking)
        raise HTTPException(status_code=404, detail=f"{window} 窗口无数据")

    @app.get("/api/alert")
    def alert(codes: str = Query("", description="逗号分隔的股票代码")) -> dict:
        wanted = {c.strip() for c in codes.split(",") if c.strip()}
        snapshot = repo.load(_resolve(None))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="无快照")
        return {
            item.base.code: stock_to_dict(item)["alert"]
            for item in snapshot.stocks
            if item.base.code in wanted and item.alert is not None
        }

    @app.get("/api/live")
    def live(ticks: int = Query(3, ge=1, le=600), interval: float = Query(5.0, gt=0, le=60)) -> StreamingResponse:
        """SSE 实时流：推送指数与涨幅摘要。"""

        def generate() -> Iterator[str]:
            for _ in range(ticks):
                snapshot = repo.load(_resolve(None))
                if snapshot is not None:
                    payload = {
                        "day": snapshot.day.isoformat(),
                        "indexes": [
                            {"code": i.base.code, "name": i.base.name,
                             "close": i.quote.close if i.quote else None,
                             "change_pct": i.quote.change_pct if i.quote else None}
                            for i in snapshot.indexes
                        ],
                    }
                    yield f"data: {payload}\n\n"
                time.sleep(interval)

        return StreamingResponse(generate(), media_type="text/event-stream")

    return app
