"""东财适配器：把第三方 JSONP/接口响应转成本地实体（结构只出现在本层）。"""
from __future__ import annotations

import json
import urllib.request
from collections.abc import Iterable

from ..domain.aggregates import PoolEntry as StockRow

_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121 Safari/537.36",
    "Referer": "https://quote.eastmoney.com/",
}
_QUOTE = (
    "https://push2.eastmoney.com/api/qt/stock/get?fltt=2&invt=2"
    "&ut=fa5fd1943c7b386f172d6893dbfba10b&fields=f43,f58,f168,f170&secid="
)


def _secid(code: str) -> str:
    return ("1." if code.startswith("6") else "0.") + code


def _get(url: str, timeout: int = 8) -> dict:
    req = urllib.request.Request(url, headers=_HEADERS)
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode("utf-8"))


class EastmoneyAdapter:
    def snapshot(self, codes: Iterable[str]) -> dict[str, StockRow]:
        out: dict[str, StockRow] = {}
        for code in codes:
            try:
                data = (_get(_QUOTE + _secid(code)).get("data")) or {}
            except (OSError, ValueError, KeyError):
                # 单只失败不影响整批；主备组合会走备源补齐
                continue
            if not data:
                continue
            out[code] = StockRow(
                code=code,
                name=data.get("f58") or code,
                pct=float(data.get("f170") or 0),
                turnover=float(data.get("f168") or 0),
            )
        return out
