"""股票：基础、行情与异动。"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from .common import Board, Exchange
from .theme_binding import StockTheme


class LimitState(str, Enum):
    """当日涨跌停状态。"""

    NONE = "NONE"
    UP = "UP"            # 涨停
    DOWN = "DOWN"        # 跌停
    BROKEN = "BROKEN"    # 炸板（触板未封）


class AlertLevel(str, Enum):
    """严重异动级别。"""

    TRIGGERED = "TRIGGERED"  # 已触发
    NEAR = "NEAR"            # 距触发 ≤2%
    WATCH = "WATCH"          # 距触发 ≤5%
    FAR = "FAR"              # 更远或未入榜


@dataclass(frozen=True)
class StockBase:
    """股票基础数据（低频，日更）。

    Attributes:
        code: 6 位代码。
        name: 简称。
        exchange: 交易所。
        board: 上市板块，决定涨跌停幅度。
        industry: 东财三级行业 ``(一级, 二级, 三级)``。
        themes: F10 核心题材标签，按重要性排序。
        list_date: 上市日，用于判定次新。
        is_st: 是否 ST/退市整理。
        float_market_cap: 流通市值（元）。
    """

    code: str
    name: str
    exchange: Exchange
    board: Board
    industry: tuple[str, str, str] = ("", "", "")
    themes: tuple[str, ...] = ()
    list_date: date | None = None
    is_st: bool = False
    float_market_cap: float = 0.0


@dataclass(frozen=True)
class StockQuote:
    """股票行情（高频，盘中秒级）。

    Attributes:
        code: 股票代码。
        day: 交易日。
        ts: 行情时间戳。
        open/high/low/close: 当日开高低收（元）。
        prev_close: 昨收（元）。
        change/pct: 涨跌额（元）与涨跌幅（%）。
        volume: 成交量（股）。
        amount: 成交额（元）。
        turnover: 换手率（%）。
        volume_ratio: 量比。
        amplitude: 振幅（%）。
        auction_pct: 集合竞价涨跌幅（%）。
        limit_state: 当日涨跌停状态。
        consecutive_limit_up: 连板数，非涨停为 0。
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
    pct: float
    volume: float = 0.0
    amount: float = 0.0
    turnover: float = 0.0
    volume_ratio: float = 0.0
    amplitude: float = 0.0
    auction_pct: float = 0.0
    limit_state: LimitState = LimitState.NONE
    consecutive_limit_up: int = 0


@dataclass(frozen=True)
class StockAlert:
    """股票异动数据（交易所严重异常波动监控）。

    Attributes:
        code: 股票代码。
        day: 监控日。
        level: 触发级别。
        rule: 规则原文，如「连续十个交易日内…+100%」。
        dev_pct: 当前累计偏离值（%）。
        threshold_pct: 规则阈值（%，如 100）。
        need_pct: 当日收盘需达到的涨幅才触发（%）。
        current_pct: 当日当前涨幅（%）。
        distance_pct: 距触发还差（%）。
        triggered_day: 已触发时的触发日。
        monitor_end: 监管期结束日（触发日 +10 个交易日）。
    """

    code: str
    day: date
    level: AlertLevel
    rule: str = ""
    dev_pct: float = 0.0
    threshold_pct: float = 0.0
    need_pct: float = 0.0
    current_pct: float = 0.0
    distance_pct: float = 0.0
    triggered_day: date | None = None
    monitor_end: date | None = None


@dataclass(frozen=True)
class Stock:
    """股票聚合：基础 + 行情 + 异动。"""

    base: StockBase
    quote: StockQuote | None = None
    alert: StockAlert | None = None
    themes: tuple[StockTheme, ...] = ()

    def theme_on(self, day) -> StockTheme | None:
        """取指定交易日的唯一题材归属。

        Args:
            day: 交易日。

        Returns:
            生效的题材段；无归属返回 None。

        Raises:
            ValueError: 同日命中多个题材段（数据冲突）。
        """
        hits = [t for t in self.themes if t.covers(day)]
        if len(hits) > 1:
            raise ValueError(f"同日多题材: code={self.base.code} day={day}")
        return hits[0] if hits else None
