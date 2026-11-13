"""东财板块成分适配器：按板块取同行业标的，用于题材「带面」。"""
from __future__ import annotations

import json
import time
import urllib.request
from collections.abc import Callable

_HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://quote.eastmoney.com/"}
_URL = (
    "https://push2.eastmoney.com/api/qt/clist/get?pn=1&pz={limit}&po=1&np=1"
    "&fltt=2&invt=2&fid=f3&fs=b:{board}&fields=f12,f14,f3"
)
Fetch = Callable[[str], str]


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(url, headers=_HEADERS)
    return urllib.request.urlopen(request, timeout=10).read().decode("utf-8", "ignore")


class EastmoneySectorAdapter:
    """实现 SectorPort：板块涨幅靠前的成分股。

    Args:
        fetch: HTTP 取数函数，注入后便于测试。
    """

    def __init__(self, fetch: Fetch | None = None, delay: float = 0.25) -> None:
        self._fetch = fetch or _default_fetch
        self._delay = delay

    def constituents(self, board_code: str, limit: int = 6) -> list[tuple[str, str]]:
        """取板块内涨幅靠前的成分股。

        Args:
            board_code: 板块代码，如 ``BK1613``。
            limit: 条数上限。

        Returns:
            (代码, 名称) 列表；接口失败返回空。
        """
        if not board_code:
            return []
        payload = None
        for attempt in range(2):
            try:
                payload = json.loads(self._fetch(_URL.format(limit=limit, board=board_code)))
                break
            except (OSError, ValueError):
                time.sleep(self._delay * (attempt + 1))
        if payload is None:
            return []
        if payload.get("rc") not in (0, None):
            return []
        rows = ((payload.get("data") or {}).get("diff")) or []
        return [
            (str(row.get("f12")), str(row.get("f14")))
            for row in rows
            if row.get("f12") and row.get("f14")
        ]
