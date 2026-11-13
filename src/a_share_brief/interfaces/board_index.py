"""指数卡序列：抓当日 60 根日 K，替换归档历史。"""
from __future__ import annotations

from typing import Any

from ..infrastructure.tencent_kline import TencentKLineAdapter

_IDS = {"上证指数": "000001", "上证综指": "000001", "深证成指": "399001",
        "科创50": "000688", "创业板指": "399006"}
_CACHE: dict[tuple[str, int], dict[str, Any]] = {}


def build_index_bars(day: str, revision: int, klines: TencentKLineAdapter) -> dict[str, Any]:
    """返回指数日 K 与日期序列。

    Args:
        day: 交易日。
        revision: 快照版本（缓存键）。
        klines: 日 K 适配器。

    Returns:
        ``{"dates": [...], "bars": {指数名: [bar...]}}``。
    """
    key = (day, revision)
    if key in _CACHE:
        return _CACHE[key]
    dates: list[str] = []
    bars: dict[str, Any] = {}
    for name, code in _IDS.items():
        try:
            rows = klines.daily(code, 60)
        except (OSError, ValueError):
            continue
        if not rows:
            continue
        if not dates:
            dates = [bar.day for bar in rows]
        bars[name] = rows
    payload = {"dates": dates, "bars": bars}
    if dates:
        _CACHE.clear()
        _CACHE[key] = payload
    return payload
