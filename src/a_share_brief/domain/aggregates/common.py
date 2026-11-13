"""公共枚举：交易所与板块。"""
from __future__ import annotations

from enum import Enum


class Exchange(str, Enum):
    """交易所。"""

    SH = "SH"
    SZ = "SZ"
    BJ = "BJ"


class Board(str, Enum):
    """上市板块，决定涨跌停幅度。"""

    MAIN = "MAIN"        # 主板 ±10%
    GEM = "GEM"          # 创业板 ±20%
    STAR = "STAR"        # 科创板 ±20%
    BSE = "BSE"          # 北交所 ±30%
