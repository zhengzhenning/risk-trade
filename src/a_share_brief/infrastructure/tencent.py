"""腾讯行情适配器：东财不可用时的兜底实现（同一端口）。"""
from __future__ import annotations

import urllib.request
from collections.abc import Iterable

from ..domain.aggregates import PoolEntry as StockRow

_URL = "https://qt.gtimg.cn/q="
_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}


def _symbol(code: str) -> str:
    return ("sh" if code.startswith("6") else "sz") + code


class TencentAdapter:
    def snapshot(self, codes: Iterable[str]) -> dict[str, StockRow]:
        codes = list(codes)
        if not codes:
            return {}
        url = _URL + ",".join(_symbol(c) for c in codes)
        try:
            raw = urllib.request.urlopen(
                urllib.request.Request(url, headers=_HEADERS), timeout=10
            ).read().decode("gbk", "ignore")
        except (OSError, ValueError, KeyError):
            # 备源也不可用时返回空，由调用方决定降级策略
            return {}

        out: dict[str, StockRow] = {}
        for line in raw.strip().split(";"):
            if "=" not in line:
                continue
            fields = line.split("=", 1)[1].strip().strip('"').split("~")
            if len(fields) < 40:
                continue
            try:
                out[fields[2]] = StockRow(
                    code=fields[2],
                    name=fields[1],
                    pct=float(fields[32] or 0),
                    turnover=float(fields[38] or 0),
                )
            except ValueError:
                continue
        return out
