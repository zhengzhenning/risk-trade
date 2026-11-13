"""东财行情适配器：把第三方字段映射为股票聚合。"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Iterable
from datetime import date

from ..domain.aggregates import Stock, StockBase, StockQuote
from ..domain.services.security import board_of, exchange_of

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}
_QUOTE = (
    "https://push2.eastmoney.com/api/qt/stock/get?fltt=2&invt=2"
    "&ut=fa5fd1943c7b386f172d6893dbfba10b"
    "&fields=f43,f44,f45,f46,f47,f48,f58,f60,f168,f169,f170&secid={secid}"
)
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=10).read().decode("utf-8", "ignore")


def secid_of(code: str) -> str:
    """把 6 位代码转成东财 secid。

    Args:
        code: 6 位证券代码。

    Returns:
        沪市 ``1.`` 前缀，其余 ``0.`` 前缀。
    """
    return ("1." if code.startswith(("6", "9")) else "0.") + code


class EastmoneyAdapter:
    """实现 QuotePort：逐只取实时行情。

    Args:
        fetch: HTTP 取数函数，注入后便于测试。
    """

    def __init__(self, fetch: Fetch | None = None) -> None:
        self._fetch = fetch or _default_fetch

    def snapshot(self, codes: Iterable[str], day: date | None = None) -> dict[str, Stock]:
        """批量取股票行情。

        Args:
            codes: 股票代码集合。
            day: 交易日，默认今天。

        Returns:
            代码到股票聚合的映射；单只失败跳过。
        """
        trade_day = day or date.today()
        result: dict[str, Stock] = {}
        for code in codes:
            try:
                data = (json.loads(self._fetch(_QUOTE.format(secid=secid_of(code)))).get("data")) or {}
                stock = _to_stock(code, trade_day, data)
            except (OSError, ValueError, KeyError):
                continue
            if stock is not None:
                result[code] = stock
        return result


def _to_stock(code: str, day: date, data: dict) -> Stock | None:
    close = data.get("f43")
    if close in (None, "-"):
        return None
    quote = StockQuote(
        code=code,
        day=day,
        ts=f"{day.isoformat()}T15:00:00+08:00",
        open=float(data.get("f46") or 0),
        high=float(data.get("f44") or 0),
        low=float(data.get("f45") or 0),
        close=float(close),
        prev_close=float(data.get("f60") or 0),
        change=float(data.get("f169") or 0),
        pct=float(data.get("f170") or 0),
        volume=float(data.get("f47") or 0),
        amount=float(data.get("f48") or 0),
        turnover=float(data.get("f168") or 0),
    )
    base = StockBase(
        code=code,
        name=str(data.get("f58") or code),
        exchange=exchange_of(code),
        board=board_of(code),
    )
    return Stock(base=base, quote=quote)
