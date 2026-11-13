#!/usr/bin/env python3
"""历史归档导入：把 archives/*.html 内的数据块还原为快照文件。

用法：
  PYTHONPATH=src python3 scripts/import_archives.py --archives archives --out work/store

口径：
  - 月度窗口取 POOLCHG.rankRows（前七）与 tailRows（8-10）；
  - 近 60 日窗口取 D10CHG.rankRows；
  - 个股取 STOCKS；指数取 MKT.idx；
  - 缺失块直接跳过，不补造数据。
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import date
from pathlib import Path

from a_share_brief.domain.aggregates import (
    Board,
    Briefing,
    Exchange,
    Index,
    IndexBase,
    IndexQuote,
    PoolEntry,
    PoolRanking,
    PoolWindow,
    Stock,
    StockBase,
    StockQuote,
)
from a_share_brief.domain.services.security import board_of, exchange_of
from a_share_brief.infrastructure.file_repo import FileRepoAdapter

BLOCK = re.compile(r"^const (\w+) = (.*?);\s*$", re.M | re.S)


def read_blocks(path: Path) -> dict:
    """解析 HTML 内的 const 数据块。

    Args:
        path: 归档文件。

    Returns:
        变量名到解析结果的映射；非 JSON 块忽略。
    """
    source = path.read_text(encoding="utf-8")
    blocks: dict = {}
    for name, payload in BLOCK.findall(source):
        try:
            blocks[name] = json.loads(payload)
        except json.JSONDecodeError:
            continue
    return blocks


def _num(value) -> float:
    try:
        return float(str(value).replace("%", "").replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def _entries(rows: list[dict], day: str, window: PoolWindow) -> list[PoolEntry]:
    """把矩阵行还原为某日排名条目。"""
    entries: list[PoolEntry] = []
    for row in rows:
        cell = (row.get("cells") or {}).get(day)
        if not cell or not cell.get("code"):
            continue
        entries.append(PoolEntry(
            code=cell["code"],
            name=cell.get("name") or cell["code"],
            rank=int(row.get("rank") or 0),
            window=window,
            range_pct=_num(cell.get("month_pct") or cell.get("d60_pct") or cell.get("range_pct")),
            pct=_num(cell.get("today_pct")),
            auction_pct=_num(cell.get("auction")),
        ))
    return sorted(entries, key=lambda e: e.rank)


def _ranking(block: dict | None, day: str, window: PoolWindow, include_tail: bool) -> PoolRanking | None:
    if not block:
        return None
    rows = list(block.get("rankRows") or [])
    if include_tail:
        rows += list(block.get("tailRows") or [])
    entries = _entries(rows, day, window)
    if not entries:
        return None
    return PoolRanking(day=date.fromisoformat(day), window=window, entries=tuple(entries))


def _stocks(rows: list[dict], day: str) -> tuple[Stock, ...]:
    stocks: list[Stock] = []
    for row in rows:
        code = str(row.get("code") or "")
        if len(code) != 6:
            continue
        board = board_of(code)
        quote = StockQuote(
            code=code,
            day=date.fromisoformat(day),
            ts=f"{day}T15:00:00+08:00",
            open=0.0, high=0.0, low=0.0, close=0.0, prev_close=0.0, change=0.0,
            pct=_num(row.get("pct")),
            turnover=_num(row.get("hs")),
        )
        stocks.append(Stock(
            base=StockBase(code=code, name=row.get("name") or code,
                           exchange=exchange_of(code), board=board),
            quote=quote,
        ))
    return tuple(stocks)


def _indexes(items: list[dict], day: str) -> tuple[Index, ...]:
    indexes: list[Index] = []
    for item in items:
        name = item.get("nm") or ""
        code = item.get("code") or ("000001" if "上证" in name else "399001")
        close = _num(item.get("close"))
        quote = IndexQuote(
            code=code,
            day=date.fromisoformat(day),
            ts=f"{day}T15:00:00+08:00",
            open=close, high=_num(item.get("hi")), low=_num(item.get("lo")),
            close=close, prev_close=close,
            change=_num(item.get("chg")), change_pct=_num(item.get("pct")),
            amount=_num(item.get("amt")) * 1e8,
        )
        indexes.append(Index(
            base=IndexBase(code=code, name=name or code, exchange=Exchange.SH),
            quote=quote,
        ))
    return tuple(indexes)


def import_one(path: Path, repo: FileRepoAdapter) -> str | None:
    """导入单个归档。

    Args:
        path: 归档文件。
        repo: 快照仓库。

    Returns:
        导入的交易日；无有效数据返回 None。
    """
    blocks = read_blocks(path)
    market = blocks.get("MKT") or {}
    day = (market.get("asOf") or (blocks.get("POOLCHG") or {}).get("today") or "").strip()
    if not day:
        return None

    rankings = tuple(
        item for item in (
            _ranking(blocks.get("POOLCHG"), day, PoolWindow.MONTH, include_tail=True),
            _ranking(blocks.get("D10CHG"), day, PoolWindow.D60, include_tail=False),
        ) if item is not None
    )
    stocks = _stocks(blocks.get("STOCKS") or [], day)
    indexes = _indexes(market.get("idx") or [], day)
    if not rankings and not stocks and not indexes:
        return None

    repo.save(Briefing(
        day=date.fromisoformat(day),
        rankings=rankings,
        indexes=indexes,
        stocks=stocks,
        revision=1,
    ))
    return day


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--archives", default="archives")
    parser.add_argument("--out", default="work/store")
    args = parser.parse_args()

    repo = FileRepoAdapter(Path(args.out))
    imported, skipped = [], []
    for path in sorted(Path(args.archives).glob("market-briefing-*.html")):
        try:
            day = import_one(path, repo)
        except (ValueError, KeyError) as exc:
            skipped.append(f"{path.name}: {exc}")
            continue
        if day:
            imported.append(day)
        else:
            skipped.append(path.name)

    print(f"导入 {len(imported)} 天: {imported[0] if imported else '-'} → {imported[-1] if imported else '-'}")
    if skipped:
        print(f"跳过 {len(skipped)} 个: {skipped[:5]}")


if __name__ == "__main__":
    main()
