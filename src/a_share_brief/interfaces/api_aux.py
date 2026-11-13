"""辅助数据路由：ETF 申赎与牛市复盘（静态导入的结构化数据）。"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query


def register_aux(app: FastAPI, root: Path) -> None:
    """注册辅助数据路由。

    Args:
        app: FastAPI 实例。
        root: 数据目录，读取 etf.json 与 history.json。
    """

    @app.get("/api/etf")
    def etf(category: Optional[str] = Query(None)) -> dict:
        path = root / "etf.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="ETF 数据未导入")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if category is None:
            return payload
        series = (payload.get("series") or {}).get(category)
        if series is None:
            raise HTTPException(status_code=400, detail=f"未知分类: {category}")
        return {"asOf": payload.get("asOf"), "type": (payload.get("types") or {}).get(category),
                "series": series}

    @app.get("/api/history/cycles")
    def cycles() -> dict:
        path = root / "history.json"
        if not path.exists():
            raise HTTPException(status_code=404, detail="复盘数据未导入")
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {"basis": payload.get("basis"), "rounds": payload.get("rounds") or [],
                "year": payload.get("year")}
