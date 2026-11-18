"""看板数据组装：把当日快照转成静态模板认识的 JSON 块。"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..domain.aggregates import Briefing
from .board_blocks import build_catalyst, build_concepts, build_peers, build_tiers
from .board_matrix import append_matrix, build_mkt

_BLOCK = re.compile(r"^const (\w+) = (.*?);\s*$", re.M | re.S)


def read_blocks(html: str) -> dict[str, Any]:
    """解析模板/归档中的 JSON 数据块。

    Args:
        html: 页面文本。

    Returns:
        变量名到解析结果的映射；非 JSON 块跳过。
    """
    blocks: dict[str, Any] = {}
    for name, payload in _BLOCK.findall(html):
        try:
            blocks[name] = json.loads(payload)
        except json.JSONDecodeError:
            continue
    return blocks


def build_stocks(briefing: Briefing, theme_of: dict[str, str],
                 quotes: dict[str, float] | None = None) -> list[dict[str, Any]]:
    """组装个股行数据。"""
    month = next((r for r in briefing.rankings if r.window.value == "MONTH"), None)
    rank_of = {e.code: e.rank for e in (month.entries if month else ())}
    d60 = next((r for r in briefing.rankings if r.window.value == "D60"), None)
    d60_codes = {e.code for e in (d60.entries if d60 else ())}
    rows = []
    seen: set[str] = set()
    for stock in briefing.stocks:
        # 同一标的可能同时命中两个窗口，去重只保留名次更好的一条
        if stock.base.code in seen:
            continue
        seen.add(stock.base.code)
        rows.append({
            "code": stock.base.code,
            "name": stock.base.name,
            "pool": "month" if stock.base.code in rank_of else "d60",
            "rk": rank_of.get(stock.base.code),
            "pct": round((quotes or {}).get(stock.base.code, stock.quote.pct if stock.quote else 0.0), 2),
            "hs": round(stock.quote.turnover, 2) if stock.quote else None,
            "jj": 0.0,
            "top": stock.base.code in rank_of and stock.base.code in d60_codes,
            "theme": theme_of.get(stock.base.code, ""),
        })
    return rows


def build_alerts(briefing: Briefing) -> dict[str, Any]:
    """组装异动块。"""
    out: dict[str, Any] = {}
    for stock in briefing.stocks:
        alert = stock.alert
        if alert is None:
            continue
        out[stock.base.code] = {
            "name": stock.base.name,
            "today": [{"rule": alert.rule or "严重异动预测", "days": 9,
                       "dev": alert.dev_pct, "need": alert.need_pct,
                       "now": alert.current_pct, "dist": alert.distance_pct}],
            "next": [],
            "triggered": ([{"date": alert.triggered_day.isoformat(),
                            "rule": alert.rule, "monitorEnd": alert.monitor_end.isoformat() if alert.monitor_end else ""}]
                          if alert.triggered_day else []),
            "level": alert.level.value.lower(),
        }
    return out


def build_themes(briefing: Briefing) -> list[dict[str, Any]]:
    """组装题材块。"""
    rows = []
    for theme in briefing.themes:
        logic = theme.logic
        desc = theme.narrative or (logic.trigger if logic else "") or "—"
        rows.append({"name": theme.name, "desc": desc, "news": []})
    return rows


def render(html: str, briefing: Briefing, day: str, vp: dict | None = None,
           index_series: dict | None = None, quotes: dict[str, float] | None = None,
           indexes: dict[str, tuple[float, float]] | None = None) -> str:
    """把快照数据写回页面。

    Args:
        html: 模板或归档页面。
        briefing: 当日快照。
        day: 交易日（ISO）。

    Returns:
        替换数据块后的页面。
    """
    blocks = read_blocks(html)
    theme_of = {
        member.code: theme.name
        for theme in briefing.themes
        for member in theme.members
    }
    replacements: dict[str, Any] = {
        "STOCKS": build_stocks(briefing, theme_of, quotes),
        "ALERTS": build_alerts(briefing),
        "THEMES": build_themes(briefing),
        "POOLCHG": append_matrix(blocks.get("POOLCHG"), briefing, day, "MONTH", "month_pct"),
        "D10CHG": append_matrix(blocks.get("D10CHG"), briefing, day, "D60", "d60_pct", top_n=7, tail_n=7),
        "MKT": build_mkt(blocks.get("MKT"), briefing, day, indexes,
                         (index_series or {}).get("bars"), (index_series or {}).get("dates")),
        "CATALYST": build_catalyst(briefing),
        "CONCEPTS": build_concepts(briefing, theme_of),
        "TIERS": build_tiers(briefing),
        "PEERS": build_peers(briefing, theme_of),
        "VP": ({**blocks.get("VP", {}), **vp} if vp else None),

    }
    out = html
    from datetime import datetime

    stamp = datetime.now().strftime("%H:%M")
    out = re.sub(r'(<div class="nav-date[^"]*">)[^<]*(</div>)',
                 rf'\g<1>{day} · 快照 {stamp}\g<2>', out, count=1)
    out = out.replace("实时数据不可用", "实时快照")
    for name, value in replacements.items():
        if value is None or (name == "VP" and not value):
            continue
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        out = re.sub(rf"^const {name} = .*?;\s*$", f"const {name} = {payload};",
                     out, count=1, flags=re.M | re.S)
    return out


def latest_archive(archives: Path) -> Path | None:
    """取最新归档文件。"""
    files = sorted(archives.glob("market-briefing-*.html"))
    return files[-1] if files else None
