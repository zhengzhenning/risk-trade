"""腾讯日 K 适配器：东财 K 线不可用时的备选实现。"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable

from ..domain.aggregates import Bar

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
_URL = "https://web.ifzq.gtimg.cn/appstock/app/fqkline/get?param={symbol},{period},,,{bars},qfq"
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=15).read().decode("utf-8", "ignore")


_INDEX_MARKET = {"000001": "sh", "000688": "sh", "399001": "sz", "399006": "sz"}


def symbol_of(code: str) -> str:
    """把 6 位代码转成腾讯行情代码。

    Args:
        code: 6 位证券代码。

    Returns:
        沪市 ``sh`` 前缀，其余 ``sz``。
    """
    market = _INDEX_MARKET.get(code)
    if market:
        return market + code
    return ("sh" if code.startswith("6") else "sz") + code


class TencentKLineAdapter:
    """实现 KLinePort：返回前复权日 K。

    Args:
        fetch: HTTP 取数函数，注入后便于测试。
    """

    def __init__(self, fetch: Fetch | None = None) -> None:
        self._fetch = fetch or _default_fetch

    def daily(self, code: str, bars: int = 120) -> list[Bar]:
        """拉取日 K。

        Args:
            code: 6 位代码。
            bars: 需要的交易日数量。

        Returns:
            按时间升序的 K 线；接口无数据返回空列表。
        """
        symbol = symbol_of(code)
        payload = json.loads(self._fetch(_URL.format(symbol=symbol, period="day", bars=bars)))
        block = ((payload.get("data") or {}).get(symbol)) or {}
        rows = block.get("qfqday") or block.get("day") or []
        bars: list[Bar] = []
        prev_close: float | None = None
        for row in rows:
            if len(row) < 6:
                continue
            bar = _to_bar(row, prev_close)
            bars.append(bar)
            prev_close = bar.close
        return bars


    def weekly(self, code: str, bars: int = 52) -> list[Bar]:
        """拉取周 K。

        Args:
            code: 6 位代码。
            bars: 周数。

        Returns:
            按时间升序的周 K；接口无数据返回空列表。
        """
        symbol = symbol_of(code)
        payload = json.loads(self._fetch(_URL.format(symbol=symbol, period="week", bars=bars)))
        block = ((payload.get("data") or {}).get(symbol)) or {}
        rows = block.get("qfqweek") or block.get("week") or []
        result: list[Bar] = []
        prev_close: float | None = None
        for row in rows:
            if len(row) < 6:
                continue
            bar = _to_bar(row, prev_close)
            result.append(bar)
            prev_close = bar.close
        return result


def _to_bar(row: list, prev_close: float | None) -> Bar:
    day, open_price, close, high, low, volume = row[:6]
    close_price = float(close)
    pct = round((close_price / prev_close - 1) * 100, 2) if prev_close else 0.0
    return Bar(
        day=day,
        open=float(open_price),
        close=close_price,
        low=float(low),
        high=float(high),
        volume=float(volume),
        pct=pct,
    )
