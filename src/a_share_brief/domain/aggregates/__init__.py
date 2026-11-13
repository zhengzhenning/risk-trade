"""领域模型包：按业务聚合拆分，对外统一导出。

模块划分：
    common   交易所与板块
    market   指数与日 K
    stock    股票基础/行情/异动
    pool     动态股池
    theme    题材与切换
    briefing 看板快照
"""
from __future__ import annotations

from .briefing import Briefing, Phase
from .common import Board, Exchange
from .market import Bar, Index, IndexBase, IndexCategory, IndexQuote
from .pool import PoolDiff, PoolEntry, PoolMatrix, PoolRanking, PoolWindow, RankCell
from .stock import AlertLevel, LimitState, Stock, StockAlert, StockBase, StockQuote
from .theme import (
    LogicLayer,
    MainUpLogic,
    StockRole,
    Theme,
    ThemeCategory,
    ThemeMember,
    ThemeStatus,
)
from .theme_binding import StockTheme, ThemeSwitch

__all__ = [
    "AlertLevel", "Bar", "Board", "Briefing", "Exchange", "Index", "IndexBase",
    "IndexCategory", "IndexQuote", "LimitState", "LogicLayer", "MainUpLogic",
    "Phase", "PoolDiff", "PoolEntry", "PoolMatrix", "PoolRanking", "PoolWindow",
    "RankCell", "Stock", "StockAlert", "StockBase", "StockQuote", "StockRole",
    "StockTheme", "Theme", "ThemeCategory", "ThemeMember", "ThemeStatus",
    "ThemeSwitch",
]
