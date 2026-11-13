"""看板数据组装：把当日快照转成静态模板认识的 JSON 块。"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from ..domain.aggregates import Briefing

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


def build_stocks(briefing: Briefing, theme_of: dict[str, str]) -> list[dict[str, Any]]:
    """组装个股行数据。"""
    month = next((r for r in briefing.rankings if r.window.value == "MONTH"), None)
    rank_of = {e.code: e.rank for e in (month.entries if month else ())}
    d60 = next((r for r in briefing.rankings if r.window.value == "D60"), None)
    d60_codes = {e.code for e in (d60.entries if d60 else ())}
    rows = []
    for stock in briefing.stocks:
        rows.append({
            "code": stock.base.code,
            "name": stock.base.name,
            "pool": "month" if stock.base.code in rank_of else "d60",
            "rk": rank_of.get(stock.base.code),
            "pct": round(stock.quote.pct, 2) if stock.quote else 0.0,
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


def append_matrix(
    base: dict[str, Any] | None,
    briefing: Briefing,
    day: str,
    window: str,
    pct_key: str,
    top_n: int = 7,
    tail_n: int = 10,
) -> dict[str, Any] | None:
    """在矩阵基础数据上追加当日列。"""
    if not base:
        return None
    ranking = next((r for r in briefing.rankings if r.window.value == window), None)
    if ranking is None:
        return base
    out = json.loads(json.dumps(base))
    dates = list(out.get("dates") or [])
    if day not in dates:
        dates.append(day)
    out["dates"] = dates
    labels = dict(out.get("labels") or {})
    labels[day] = day[5:7] + day[8:10] + "周" + "一二三四五六日"[date.fromisoformat(day).weekday()]
    out["labels"] = labels
    out["today"] = day

    cells_by_rank = {entry.rank: entry for entry in ranking.entries}
    rows = list(out.get("rankRows") or [])
    tail = list(out.get("tailRows") or out.get("tail") or [])
    for row in rows:
        cell = cells_by_rank.get(int(row.get("rank") or 0))
        if cell is not None:
            row.setdefault("cells", {})[day] = {"code": cell.code, "name": cell.name,
                                                pct_key: f"{cell.range_pct:.2f}"}
    for row in tail:
        cell = cells_by_rank.get(int(row.get("rank") or 0))
        if cell is not None:
            row.setdefault("cells", {})[day] = {"code": cell.code, "name": cell.name,
                                                pct_key: f"{cell.range_pct:.2f}"}
    out["rankRows"] = rows
    if tail:
        out["tailRows"] = tail
    return out


def build_mkt(base: dict[str, Any] | None, briefing: Briefing, day: str) -> dict[str, Any] | None:
    """更新大盘块：日期与指数当日值。"""
    if not base:
        return None
    out = json.loads(json.dumps(base))
    out["asOf"] = day
    dates = list(out.get("dates") or [])
    # 保持与 idx[].O 等长：只替换最后一天，不追加
    if dates:
        dates[-1] = day
    out["dates"] = dates
    window = dict(out.get("window") or {})
    if window:
        window["to"] = day
        out["window"] = window
    by_name = {item.base.name: item for item in briefing.indexes}

    def match(name: str):
        if name in by_name:
            return by_name[name]
        for key, value in by_name.items():
            if key[:2] == name[:2] or name[:2] in key:
                return value
        return None

    for item in out.get("idx") or []:
        quote = match(str(item.get("nm") or ""))
        if quote is None or quote.quote is None:
            continue
        item["close"] = round(quote.quote.close, 2)
        item["chg"] = round(quote.quote.change, 2)
        item["pct"] = round(quote.quote.change_pct, 2)
        item["amt"] = round(quote.quote.amount / 1e8, 1)
        series = list(item.get("O") or [])
        if series:
            series[-1] = round(quote.quote.close, 2)
            item["O"] = series
    return out


def render(html: str, briefing: Briefing, day: str) -> str:
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
        "STOCKS": build_stocks(briefing, theme_of),
        "ALERTS": build_alerts(briefing),
        "THEMES": build_themes(briefing),
        "POOLCHG": append_matrix(blocks.get("POOLCHG"), briefing, day, "MONTH", "month_pct"),
        "D10CHG": append_matrix(blocks.get("D10CHG"), briefing, day, "D60", "d60_pct", top_n=7, tail_n=7),
        "MKT": build_mkt(blocks.get("MKT"), briefing, day),
        # CATALYST/CONCEPTS/TIERS 的模板字段尚未完全对齐，先保留归档内容，避免半成品

    }
    out = html
    out = re.sub(r'(<div class="nav-date[^"]*">)[^<]*(</div>)',
                 rf'\g<1>{day} · 盘中\g<2>', out, count=1)
    out = out.replace("实时数据不可用", "实时快照")
    for name, value in replacements.items():
        if value is None:
            continue
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        out = re.sub(rf"^const {name} = .*?;\s*$", f"const {name} = {payload};",
                     out, count=1, flags=re.M | re.S)
    return out


def latest_archive(archives: Path) -> Path | None:
    """取最新归档文件。"""
    files = sorted(archives.glob("market-briefing-*.html"))
    return files[-1] if files else None


def build_catalyst(briefing: Briefing) -> dict[str, Any]:
    """主升催化：锚点主块 + 两行背景。"""
    out: dict[str, Any] = {}
    for theme in briefing.themes:
        logic = theme.logic
        chain = [
            f"触发：{logic.trigger}" if logic and logic.trigger else "",
            f"扩散：{logic.diffusion}" if logic and logic.diffusion else "",
            f"卡位：{logic.positioning}" if logic and logic.positioning else "",
        ]
        rows: list[dict[str, Any]] = [{
            "kind": "main",
            "core": (logic.trigger if logic else "") or theme.narrative or theme.name,
            "u": "",
            "chain": [item for item in chain if item],
            "evid": "；".join(logic.evidence) if logic else "",
            "risk": "",
        }]
        if logic and logic.diffusion:
            rows.append({"tag": "扩散", "t": logic.diffusion[:24], "n": logic.diffusion})
        if logic and logic.positioning:
            rows.append({"tag": "卡位", "t": logic.positioning[:24], "n": logic.positioning})
        out[theme.anchor_code] = rows
    return out


def build_concepts(briefing: Briefing, theme_of: dict[str, str]) -> dict[str, Any]:
    """个股题材与行业标签。"""
    out: dict[str, Any] = {}
    for stock in briefing.stocks:
        theme = theme_of.get(stock.base.code)
        labels = [label for label in stock.base.themes if label]
        if theme and theme not in labels:
            labels.append(theme)
        out[stock.base.code] = {
            "name": stock.base.name,
            "industry": list(stock.base.industry),
            "concepts": labels,
        }
    return out


def build_tiers(briefing: Briefing) -> dict[str, Any]:
    """题材梯队：成员与名次。"""
    out: dict[str, Any] = {}
    for theme in briefing.themes:
        out[theme.name] = [
            {"code": m.code, "name": m.name, "mp": round(m.range_pct, 2),
             "anchor": m.is_anchor, "rk": m.rank_in_pool}
            for m in theme.members
        ]
    return out
