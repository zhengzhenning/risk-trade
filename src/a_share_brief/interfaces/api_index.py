"""指数历史路由：量价全景所需的日 K 序列。"""
from __future__ import annotations

from fastapi import FastAPI, HTTPException, Query

from ..infrastructure.tencent_kline import TencentKLineAdapter

_NAMES = {"000001": "上证指数", "399001": "深证成指", "000688": "科创50"}


def register_index(app: FastAPI, klines: TencentKLineAdapter) -> None:
    """注册指数历史路由。

    Args:
        app: FastAPI 实例。
        klines: 日 K 适配器。
    """

    @app.get("/api/index/history")
    def index_history(code: str = Query("000001"), bars: int = Query(60, ge=10, le=250)) -> dict:
        if code not in _NAMES:
            raise HTTPException(status_code=400, detail=f"未知指数: {code}")
        rows = klines.daily(code, bars=bars)
        if not rows:
            raise HTTPException(status_code=502, detail="行情源不可用")
        return {
            "code": code,
            "name": _NAMES[code],
            "bars": [
                {"day": bar.day, "open": bar.open, "close": bar.close,
                 "high": bar.high, "low": bar.low, "volume": bar.volume, "pct": bar.pct}
                for bar in rows
            ],
        }
