"""指数与日 K。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .common import Exchange


class IndexCategory(str, Enum):
    """指数类别。"""

    BROAD = "BROAD"      # 宽基
    SECTOR = "SECTOR"    # 行业
    THEME = "THEME"      # 主题


@dataclass(frozen=True)
class IndexBase:
    """指数基础数据（低频，日更）。

    Attributes:
        code: 交易所代码，如 ``000001``。
        name: 简称，如 ``上证指数``。
        exchange: 所属交易所。
        category: 宽基/行业/主题。
        constituents: 成分股数量，未知为 None。
        launch_date: 发布日，未知为 None。
    """

    code: str
    name: str
    exchange: Exchange
    category: IndexCategory = IndexCategory.BROAD
    constituents: int | None = None
    launch_date: date | None = None


@dataclass(frozen=True)
class IndexQuote:
    """指数行情（高频，盘中秒级）。

    Attributes:
        code: 指数代码。
        day: 交易日。
        ts: 行情时间戳（ISO 8601，含时区）。
        open/high/low/close: 当日开高低收（点）。
        prev_close: 昨收（点）。
        change: 涨跌点数。
        change_pct: 涨跌幅（%，如 1.23 表示 +1.23%）。
        volume: 成交量（手）。
        amount: 成交额（元）。
    """

    code: str
    day: date
    ts: str
    open: float
    high: float
    low: float
    close: float
    prev_close: float
    change: float
    change_pct: float
    volume: float = 0.0
    amount: float = 0.0


@dataclass(frozen=True)
class Index:
    """指数聚合：基础 + 行情。"""

    base: IndexBase
    quote: IndexQuote | None = None


@dataclass(frozen=True)
class Bar:
    """日 K 线。"""

    day: str
    open: float
    close: float
    low: float
    high: float
    volume: float
    pct: float
    turnover: float = 0.0
