"""个股详情路由：行情、异动与威科夫阶段。"""
from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.snapshot_codec import stock_to_dict


def register_stock(app: FastAPI, repo: FileRepoAdapter, resolve) -> None:
    """注册个股详情路由。

    Args:
        app: FastAPI 实例。
        repo: 快照仓库。
        resolve: 日期解析函数。
    """

    @app.get("/api/stock/{code}")
    def stock_detail(code: str, day: Optional[str] = Query(None, alias="date")) -> dict:
        snapshot = repo.load(resolve(day))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="无快照")
        stock = next((item for item in snapshot.stocks if item.base.code == code), None)
        if stock is None:
            raise HTTPException(status_code=404, detail=f"无 {code} 数据")
        return {
            "day": snapshot.day.isoformat(),
            "stock": stock_to_dict(stock),
            "phases": [
                {"start": p.start, "end": p.end, "kind": p.kind, "note": p.note}
                for p in snapshot.phases.get(code, ())
            ],
        }
