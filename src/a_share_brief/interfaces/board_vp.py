"""威科夫块：按当日快照金额/阶段预生成，逐日缓存，避免页面重复抓 K 线。"""
from __future__ import annotations

from typing import Any

from ..domain.aggregates import Briefing
from ..domain.services.wyckoff import judge
from ..infrastructure.tencent_kline import TencentKLineAdapter

_CACHE: dict[tuple[str, int], dict[str, Any]] = {}


def build_vp(briefing: Briefing, day: str, klines: TencentKLineAdapter) -> dict[str, Any]:
    """组装 VP 块（K 线 + 阶段 + 区间统计）。

    Args:
        briefing: 当日快照。
        day: 交易日。
        klines: 日 K 适配器。

    Returns:
        代码到 VP 数据的映射；抓取失败的标的跳过。
    """
    key = (day, briefing.revision)
    if key in _CACHE:
        return _CACHE[key]

    codes = [entry.code for ranking in briefing.rankings for entry in ranking.entries][:7]
    out: dict[str, Any] = {}
    for code in dict.fromkeys(codes):
        try:
            bars = klines.daily(code, 60)
        except (OSError, ValueError):
            continue
        if len(bars) < 10:
            continue
        phases = judge(tuple(bars))
        closes = [bar.close for bar in bars]
        out[code] = {
            "k": [[bar.day, bar.open, bar.close, bar.high, bar.low, bar.volume, bar.pct, bar.turnover]
                  for bar in bars],
            "phases": [{"a": p.start, "b": p.end, "k": p.kind, "note": p.note,
                        "tent": p.tentative} for p in phases],
            "n": len(phases),
            "conf": "中" if len(phases) >= 2 else "弱",
            "sd": "供小于需" if phases and phases[-1].kind in ("acc", "wash", "start") else "供大于需",
            "sdWhy": phases[-1].note if phases else "",
            "why": {p.kind: p.note for p in phases},
            "stats": {
                "chg": f"{(closes[-1] / closes[0] - 1) * 100:.2f}",
                "close": f"{closes[-1]:.2f}",
                "lo": f"{min(bar.low for bar in bars):.2f}",
                "hi": f"{max(bar.high for bar in bars):.2f}",
            },
        }
    _CACHE.clear()
    _CACHE[key] = out
    return out
