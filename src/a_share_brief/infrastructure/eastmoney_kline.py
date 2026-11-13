"""东财日 K 适配器：腾讯不可用时的兜底。"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable

from ..domain.aggregates import Bar

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
_URL = (
    "https://push2his.eastmoney.com/api/qt/stock/kline/get?secid={secid}"
    "&fields1=f1,f2,f3&fields2=f51,f52,f53,f54,f55,f56&klt=101&fqt=1&lmt={bars}&end=20500101"
)
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=12).read().decode("utf-8", "ignore")


class EastmoneyKLineAdapter:
    """实现 KLinePort 的日 K 兜底。

    Args:
        fetch: HTTP 取数函数，便于测试。
    """

    def __init__(self, fetch: Fetch | None = None) -> None:
        self._fetch = fetch or _default_fetch

    def daily(self, code: str, bars: int = 120) -> list[Bar]:
        """拉取前复权日 K。"""
        secid = ("1." if code.startswith(("6", "9")) else "0.") + code
        payload = json.loads(self._fetch(_URL.format(secid=secid, bars=bars)))
        rows = ((payload.get("data") or {}).get("klines")) or []
        out: list[Bar] = []
        prev: float | None = None
        for row in rows:
            parts = row.split(",")
            if len(parts) < 6:
                continue
            day, open_, close, high, low, volume = parts[:6]
            close_v = float(close)
            pct = round((close_v / prev - 1) * 100, 2) if prev else 0.0
            out.append(Bar(day=day, open=float(open_), close=close_v, low=float(low),
                           high=float(high), volume=float(volume), pct=pct))
            prev = close_v
        return out
