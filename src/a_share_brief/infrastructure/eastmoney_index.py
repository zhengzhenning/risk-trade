"""东财指数行情适配器：把 secid 行情映射为指数聚合。"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Callable, Iterable
from datetime import date

from ..domain.aggregates import Exchange, Index, IndexBase, IndexQuote

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
_TENCENT = (
    "https://qt.gtimg.cn/q={symbols}"
)
_QUOTE = (
    "https://push2.eastmoney.com/api/qt/stock/get?fltt=2&invt=2"
    "&ut=fa5fd1943c7b386f172d6893dbfba10b&fields=f43,f44,f45,f46,f47,f48,f58,f60,f169,f170&secid={secid}"
)
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    raw = urllib.request.urlopen(request, timeout=10).read()
    # 腾讯行情返回 GBK，东财返回 UTF-8
    return raw.decode("gbk", "ignore") if "gtimg" in url else raw.decode("utf-8", "ignore")


def secid_of(code: str) -> str:
    """把 6 位指数代码转成东财 secid。

    Args:
        code: 指数代码，如 000001、399001、000688。

    Returns:
        沪市 ``1.`` 前缀，深市 ``0.`` 前缀。
    """
    return ("1." if code.startswith("6") or code.startswith("000") else "0.") + code


class EastmoneyIndexAdapter:
    """实现 IndexQuotePort：逐只取指数行情。

    Args:
        fetch: HTTP 取数函数，注入后便于测试。
    """

    def __init__(self, fetch: Fetch | None = None) -> None:
        self._fetch = fetch or _default_fetch

    def snapshot(self, codes: Iterable[str], day: date | None = None) -> dict[str, Index]:
        """批量取指数行情。

        Args:
            codes: 指数代码集合。
            day: 交易日，默认今天。

        Returns:
            代码到指数聚合的映射；失败或空数据跳过该只。
        """
        trade_day = day or date.today()
        code_list = list(codes)
        result: dict[str, Index] = {}
        for code in code_list:
            try:
                payload = json.loads(self._fetch(_QUOTE.format(secid=secid_of(code))))
                quote = _to_quote(code, trade_day, payload.get("data") or {})
            except (OSError, ValueError, KeyError):
                quote = None
            if quote is not None:
                result[code] = Index(
                    base=IndexBase(code=code, name=quote.name, exchange=_exchange(code)),
                    quote=quote.quote,
                )

        missing = [code for code in code_list if code not in result]
        if missing:
            result.update(self._tencent(missing, trade_day))
        return result

    def _tencent(self, codes: list[str], trade_day: date) -> dict[str, Index]:
        """东财不可用时的指数兜底。

        Args:
            codes: 待补齐的指数代码。
            trade_day: 交易日。

        Returns:
            代码到指数聚合的映射；解析失败的跳过。
        """
        symbols = ",".join(("sh" if c.startswith("6") or c.startswith("000") else "sz") + c for c in codes)
        try:
            raw = self._fetch(_TENCENT.format(symbols=symbols))
        except (OSError, ValueError):
            return {}
        out: dict[str, Index] = {}
        for line in raw.strip().split(";"):
            if "=" not in line:
                continue
            fields = line.split("=", 1)[1].strip().strip('"').split("~")
            if len(fields) < 40:
                continue
            code = fields[2]
            if code not in codes:
                continue
            out[code] = Index(
                base=IndexBase(code=code, name=fields[1], exchange=_exchange(code)),
                quote=IndexQuote(
                    code=code,
                    day=trade_day,
                    ts=fields[30] or f"{trade_day.isoformat()}T15:00:00+08:00",
                    open=float(fields[5] or 0),
                    high=float(fields[33] or 0),
                    low=float(fields[34] or 0),
                    close=float(fields[3] or 0),
                    prev_close=float(fields[4] or 0),
                    change=float(fields[31] or 0),
                    change_pct=float(fields[32] or 0),
                    volume=float(fields[36] or 0),
                    amount=float(fields[37] or 0) * 1e4,
                ),
            )
        return out


def _exchange(code: str) -> Exchange:
    return Exchange.SH if code.startswith("6") or code.startswith("000") else Exchange.SZ


class _Mapped:
    """内部映射结果，避免在循环里构造两次聚合。"""

    def __init__(self, name: str, quote: IndexQuote) -> None:
        self.name = name
        self.quote = quote


def _to_quote(code: str, day: date, data: dict) -> _Mapped | None:
    close = data.get("f43")
    if close in (None, "-"):
        return None
    return _Mapped(
        name=str(data.get("f58") or code),
        quote=IndexQuote(
            code=code,
            day=day,
            ts=f"{day.isoformat()}T15:00:00+08:00",
            open=float(data.get("f46") or 0),
            high=float(data.get("f44") or 0),
            low=float(data.get("f45") or 0),
            close=float(close),
            prev_close=float(data.get("f60") or 0),
            change=float(data.get("f169") or 0),
            change_pct=float(data.get("f170") or 0),
            volume=float(data.get("f47") or 0),
            amount=float(data.get("f48") or 0),
        ),
    )
