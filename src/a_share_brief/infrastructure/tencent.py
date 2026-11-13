"""腾讯行情适配器：东财不可用时的兜底实现（同一端口）。"""
from __future__ import annotations

import urllib.request
from collections.abc import Callable, Iterable
from datetime import date

from ..domain.aggregates import Stock, StockBase, StockQuote
from ..domain.services.security import board_of, exchange_of

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
_URL = "https://qt.gtimg.cn/q={symbols}"
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=10).read().decode("gbk", "ignore")


def symbol_of(code: str) -> str:
    """把 6 位代码转成腾讯行情代码。

    Args:
        code: 6 位证券代码。

    Returns:
        沪市 ``sh`` 前缀，其余 ``sz``。
    """
    return ("sh" if code.startswith("6") else "sz") + code


class TencentAdapter:
    """实现 QuotePort：批量取实时行情。

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
            代码到股票聚合的映射；接口失败返回空字典。
        """
        code_list = list(dict.fromkeys(codes))
        if not code_list:
            return {}
        trade_day = day or date.today()
        result = self._parse(self._fetch(_URL.format(symbols=",".join(map(symbol_of, code_list)))),
                             code_list, trade_day)

        # 批量偶发漏返（停牌或字段不足）时逐只补取一次
        for code in (item for item in code_list if item not in result):
            try:
                single = self._fetch(_URL.format(symbols=symbol_of(code)))
            except (OSError, ValueError):
                continue
            result.update(self._parse(single, [code], trade_day))
        return result

    @staticmethod
    def _parse(raw: str, wanted: list[str], trade_day: date) -> dict[str, Stock]:
        out: dict[str, Stock] = {}
        for line in raw.strip().split(";"):
            if "=" not in line:
                continue
            fields = line.split("=", 1)[1].strip().strip('"').split("~")
            if len(fields) < 40 or fields[2] not in wanted:
                continue
            code = fields[2]
            out[code] = Stock(
                base=StockBase(code=code, name=fields[1], exchange=exchange_of(code),
                               board=board_of(code)),
                quote=StockQuote(
                    code=code,
                    day=trade_day,
                    ts=f"{trade_day.isoformat()}T15:00:00+08:00",
                    open=float(fields[5] or 0),
                    high=float(fields[33] or 0),
                    low=float(fields[34] or 0),
                    close=float(fields[3] or 0),
                    prev_close=float(fields[4] or 0),
                    change=float(fields[31] or 0),
                    pct=float(fields[32] or 0),
                    volume=float(fields[36] or 0),
                    amount=float(fields[37] or 0) * 1e4,
                    turnover=float(fields[38] or 0),
                ),
            )
        return out
