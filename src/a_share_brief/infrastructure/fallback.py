"""组合适配器：主源缺失时用备源补齐，调用方只看到行情端口。"""
from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import date

from ..application.ports import QuotePort
from ..domain.aggregates import Stock

_LOG = logging.getLogger(__name__)


class FallbackQuotes:
    """主备行情组合。

    Args:
        primary: 主源，通常为东财。
        secondary: 备源，主源缺失时补齐。
    """

    def __init__(self, primary: QuotePort, secondary: QuotePort) -> None:
        self._primary = primary
        self._secondary = secondary

    def snapshot(self, codes: Iterable[str], day: date | None = None) -> dict[str, Stock]:
        """返回行情快照，缺失标的由备源补齐。

        Args:
            codes: 股票代码集合。
            day: 交易日。

        Returns:
            代码到股票聚合的映射；两源都缺失的代码不出现。
        """
        code_list = list(codes)
        out = dict(self._primary.snapshot(code_list, day=day))
        missing = [c for c in code_list if c not in out]
        if missing:
            _LOG.warning("primary quote miss codes=%s, fallback to secondary", missing)
            out.update(self._secondary.snapshot(missing, day=day))
        return out
