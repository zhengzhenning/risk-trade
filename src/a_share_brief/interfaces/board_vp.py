"""威科夫块：按当日快照金额/阶段预生成，逐日缓存，避免页面重复抓 K 线。"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from ..domain.aggregates import Briefing
from ..domain.services.wyckoff import judge
from ..infrastructure.eastmoney_kline import EastmoneyKLineAdapter
from ..infrastructure.fallback_kline import FallbackKLine
from ..infrastructure.tencent_kline import TencentKLineAdapter

_CACHE: dict[str, dict[str, Any]] = {}
_CACHE_AT: dict[str, float] = {}
TTL_SECONDS = 180.0
_CACHE_DIR = Path("work/cache")


def _load_disk(day: str) -> dict[str, Any] | None:
    path = _CACHE_DIR / f"vp-{day}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _save_disk(day: str, payload: dict[str, Any]) -> None:
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)
    (_CACHE_DIR / f"vp-{day}.json").write_text(
        json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def build_vp(briefing: Briefing, day: str, klines=None) -> dict[str, Any]:
    """组装 VP 块（K 线 + 阶段 + 区间统计）。

    Args:
        briefing: 当日快照。
        day: 交易日。
        klines: 日 K 适配器。

    Returns:
        代码到 VP 数据的映射；抓取失败的标的跳过。
    """
    klines = klines or FallbackKLine(TencentKLineAdapter(), EastmoneyKLineAdapter())
    fresh = (day in _CACHE and time.time() - _CACHE_AT.get(day, 0) < TTL_SECONDS)
    # 过期后不再拿旧 K 线复用，只作为抓取失败时的兜底
    cached = dict(_CACHE.get(day) or {}) if fresh else {}
    fallback = {} if fresh else dict(_load_disk(day) or {})

    codes = [entry.code for ranking in briefing.rankings for entry in ranking.entries][:7]
    out: dict[str, Any] = {}
    for code in dict.fromkeys(codes):
        if len((cached.get(code) or {}).get("k") or []) >= 10:
            out[code] = cached[code]        # 已有真实数据，直接复用
            continue
        try:
            bars = klines.daily(code, 60)
        except Exception:  # 单只失败跳过，代理层已有自己的重试
            bars = []
        if len(bars) < 10:
            # K 线源不可用：用快照收盘价造一根占位 K，保证 Tab 与前七一致
            quote = next((x.quote for x in briefing.stocks if x.base.code == code), None)
            close = quote.close if quote else 0.0
            day_row = [briefing.day.isoformat(), close, close, close, close, 0.0,
                       quote.pct if quote else 0.0, quote.turnover if quote else 0.0]
            phases = briefing.phases.get(code, ())
            out[code] = {
                "k": [day_row, day_row],
                "phases": [{"a": ph.start, "b": ph.end, "k": ph.kind, "note": ph.note,
                            "tent": ph.tentative} for ph in phases],
                "n": len(phases),
                "conf": "弱",
                "sd": "—",
                "sdWhy": "",
                "why": {ph.kind: ph.note for ph in phases},
                "stats": {"chg": "0.00", "close": f"{close:.2f}", "lo": f"{close:.2f}",
                          "hi": f"{close:.2f}"},
            }
            continue
        phases = judge(tuple(bars))
        closes = [bar.close for bar in bars]
        out[code] = {
            # 模板约定：r[3]=最低、r[4]=最高
            "k": [[bar.day, bar.open, bar.close, bar.low, bar.high, bar.volume, bar.pct, bar.turnover]
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
    # 新抓的覆盖旧的；失败标的用磁盘里的旧数据兜底
    out = {**fallback, **cached, **out}
    _CACHE.clear()
    _CACHE[day] = out
    _CACHE_AT[day] = time.time()
    # 只落盘真实 K 线，占位（<10 根）不覆盖缓存
    real = {code: vp for code, vp in out.items() if len(vp.get("k") or []) >= 10}
    if real:
        _save_disk(day, real)
    return out
