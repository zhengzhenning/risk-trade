"""看板矩阵块：在归档矩阵上追加当日列。"""
from __future__ import annotations

import json
from datetime import date
from typing import Any

from ..domain.aggregates import Briefing


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


def build_mkt(base: dict[str, Any] | None, briefing: Briefing, day: str,
              overlay: dict[str, tuple[float, float]] | None = None,
              series: dict[str, list[Any]] | None = None,
              dates: list[str] | None = None) -> dict[str, Any] | None:
    """更新大盘块：日期与指数当日值。"""
    if not base:
        return None
    out = json.loads(json.dumps(base))
    out["asOf"] = day
    base_dates = list(dates or out.get("dates") or [])
    if base_dates:
        base_dates[-1] = day
    out["dates"] = base_dates
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
        name = str(item.get("nm") or "")
        if overlay and name in overlay:
            close, pct = overlay[name]
            item["close"] = round(close, 2)
            item["pct"] = round(pct, 2)
            continue
        item["close"] = round(quote.quote.close, 2)
        item["chg"] = round(quote.quote.change, 2)
        item["pct"] = round(quote.quote.change_pct, 2)
        item["amt"] = round(quote.quote.amount / 1e8, 1)
        fresh = (series or {}).get(str(item.get("nm") or ""))
        if fresh:
            item["O"] = [round(bar.open, 2) for bar in fresh]
            item["C"] = [round(bar.close, 2) for bar in fresh]
            item["H"] = [round(bar.high, 2) for bar in fresh]
            item["L"] = [round(bar.low, 2) for bar in fresh]
            item["V"] = [bar.volume for bar in fresh]
        else:
            values = list(item.get("O") or [])
            if values:
                values[-1] = round(quote.quote.close, 2)
                item["O"] = values
    return out
