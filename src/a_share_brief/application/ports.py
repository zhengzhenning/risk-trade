"""端口：内圈契约。外部世界（东财/腾讯/PG/Redis/渲染）只能以这些接口出现。"""
from __future__ import annotations

from collections.abc import Iterable
from datetime import date
from typing import Protocol, runtime_checkable

from ..domain.aggregates import Bar, Briefing, Index, PoolEntry, Stock, StockAlert


@runtime_checkable
class QuotePort(Protocol):
    """行情端口：批量取股票实时行情。"""

    def snapshot(self, codes: Iterable[str], day: date | None = None) -> dict[str, Stock]: ...


@runtime_checkable
class IndexQuotePort(Protocol):
    """指数行情端口。"""

    def snapshot(self, codes: Iterable[str], day: date | None = None) -> dict[str, Index]: ...


@runtime_checkable
class KLinePort(Protocol):
    """日 K 线端口。"""

    def daily(self, code: str, bars: int = 120) -> list[Bar]: ...


@runtime_checkable
class PoolPort(Protocol):
    """股池端口：双窗口排名。"""

    def month_top(self, n: int = 10) -> list[PoolEntry]: ...

    def d60_top(self, n: int = 7) -> list[PoolEntry]: ...


@runtime_checkable
class AlertPort(Protocol):
    """异动端口：严重异动监控数据。"""

    def unusual(self, codes: Iterable[str], day: date | None = None) -> dict[str, StockAlert]: ...


class SnapshotRepo(Protocol):
    """快照仓库端口。"""

    def save(self, briefing: Briefing) -> None: ...

    def load(self, day: date) -> Briefing | None: ...


class BoardRenderer(Protocol):
    """渲染端口。"""

    def render(self, briefing: Briefing) -> str: ...
