"""HTTP 路由：只解析参数并读取快照，不含业务规则。"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query

from ..application.views import matrix_to_dict, theme_to_view
from ..domain.aggregates import PoolWindow
from ..domain.services.pool import matrix as build_matrix
from ..infrastructure.file_repo import FileRepoAdapter
from ..infrastructure.snapshot_codec import index_to_dict, ranking_to_dict, stock_to_dict
from .api_live import register_live

_WINDOWS = {"MONTH": PoolWindow.MONTH, "D60": PoolWindow.D60}


def available_days(root: Path) -> list[date]:
    """列出仓库中的交易日。

    Args:
        root: 快照目录。

    Returns:
        升序交易日列表。
    """
    days: list[date] = []
    for path in root.glob("briefing-*.json"):
        try:
            days.append(date.fromisoformat(path.stem.removeprefix("briefing-")))
        except ValueError:
            continue
    return sorted(days)


def resolve_day(root: Path, day: Optional[str]) -> date:
    """解析请求日期，缺省取最新交易日。

    Args:
        root: 快照目录。
        day: ISO 日期或 None。

    Returns:
        交易日。

    Raises:
        HTTPException: 日期非法返回 400；无快照返回 404。
    """
    if day:
        try:
            return date.fromisoformat(day)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"日期格式错误: {day}") from exc
    days = available_days(root)
    if not days:
        raise HTTPException(status_code=404, detail="暂无快照")
    return days[-1]


def register_routes(app: FastAPI, root: Path, repo: FileRepoAdapter) -> None:
    """注册全部路由。

    Args:
        app: FastAPI 实例。
        root: 快照目录。
        repo: 快照仓库。
    """

    def resolve(day: Optional[str]) -> date:
        return resolve_day(root, day)

    @app.get("/healthz")
    def healthz() -> dict:
        days = available_days(root)
        return {"status": "ok", "days": len(days),
                "latest": days[-1].isoformat() if days else None}

    @app.get("/api/history")
    def history() -> dict:
        return {"days": [item.isoformat() for item in available_days(root)]}

    @app.get("/api/briefing")
    def briefing(day: Optional[str] = Query(None, alias="date")) -> dict:
        target = resolve(day)
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

    @app.get("/api/pool/history")
    def pool_history(window: str = Query("MONTH"), days: int = Query(6, ge=1, le=30)) -> dict:
        target_window = _WINDOWS.get(window.upper())
        if target_window is None:
            raise HTTPException(status_code=400, detail=f"未知窗口: {window}")
        rankings = []
        for item in available_days(root)[-days:]:
            snapshot = repo.load(item)
            if snapshot is None:
                continue
            rankings.extend(r for r in snapshot.rankings if r.window is target_window)
        if not rankings:
            raise HTTPException(status_code=404, detail=f"{window} 窗口无数据")
        return matrix_to_dict(build_matrix(rankings, target_window, top_n=7, tail_n=10))

    @app.get("/api/pool/{window}")
    def pool(window: str, day: Optional[str] = Query(None, alias="date")) -> dict:
        target_window = _WINDOWS.get(window.upper())
        if target_window is None:
            raise HTTPException(status_code=400, detail=f"未知窗口: {window}")
        snapshot = repo.load(resolve(day))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="无快照")
        for ranking in snapshot.rankings:
            if ranking.window is target_window:
                return ranking_to_dict(ranking)
        raise HTTPException(status_code=404, detail=f"{window} 窗口无数据")

    @app.get("/api/themes")
    def themes(day: Optional[str] = Query(None, alias="date")) -> dict:
        snapshot = repo.load(resolve(day))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="无快照")
        return {"day": snapshot.day.isoformat(),
                "themes": [theme_to_view(item) for item in snapshot.themes]}

    @app.get("/api/alert")
    def alert(codes: str = Query("", description="逗号分隔的股票代码")) -> dict:
        wanted = {item.strip() for item in codes.split(",") if item.strip()}
        snapshot = repo.load(resolve(None))
        if snapshot is None:
            raise HTTPException(status_code=404, detail="无快照")
        return {
            item.base.code: stock_to_dict(item)["alert"]
            for item in snapshot.stocks
            if item.base.code in wanted and item.alert is not None
        }

    register_live(app, root, repo, resolve)
