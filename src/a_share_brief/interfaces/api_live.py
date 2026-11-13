"""实时流路由：SSE 推送最新快照摘要。"""
from __future__ import annotations

import time
from collections.abc import Iterator
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse

from ..infrastructure.file_repo import FileRepoAdapter


def register_live(app: FastAPI, root: Path, repo: FileRepoAdapter, resolve) -> None:
    """注册实时流路由。

    Args:
        app: FastAPI 实例。
        root: 快照目录，保留以备切换推送源。
        repo: 快照仓库。
        resolve: 日期解析函数。
    """

    @app.get("/api/live")
    def live(ticks: int = Query(3, ge=1, le=600),
             interval: float = Query(5.0, gt=0, le=60)) -> StreamingResponse:
        def generate() -> Iterator[str]:
            for _ in range(ticks):
                snapshot = repo.load(resolve(None))
                if snapshot is not None:
                    payload = {
                        "day": snapshot.day.isoformat(),
                        "indexes": [
                            {"code": item.base.code, "name": item.base.name,
                             "close": item.quote.close if item.quote else None,
                             "change_pct": item.quote.change_pct if item.quote else None}
                            for item in snapshot.indexes
                        ],
                    }
                    yield f"data: {payload}\n\n"
                time.sleep(interval)

        return StreamingResponse(generate(), media_type="text/event-stream")
