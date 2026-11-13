"""证券分类：代码到交易所与板块的映射。

板块决定涨跌停幅度，必须由代码推导，不信任外部字段。
"""
from __future__ import annotations

from ..aggregates import Board, Exchange


def exchange_of(code: str) -> Exchange:
    """按代码前缀判定交易所。

    Args:
        code: 6 位证券代码。

    Returns:
        SH 沪市、BJ 北交所、其余 SZ 深市。
    """
    if code.startswith("6"):
        return Exchange.SH
    if code.startswith(("4", "8")):
        return Exchange.BJ
    return Exchange.SZ


def board_of(code: str) -> Board:
    """按代码前缀判定上市板块。

    Args:
        code: 6 位证券代码。

    Returns:
        STAR 科创板、GEM 创业板、BSE 北交所、MAIN 主板。
    """
    if code.startswith("688"):
        return Board.STAR
    if code.startswith(("300", "301")):
        return Board.GEM
    if code.startswith(("4", "8")):
        return Board.BSE
    return Board.MAIN
